import json
from pathlib import Path

import pytest

from trainer_bot.codex_agent import CodexAgent
from trainer_bot.config import Settings


@pytest.fixture
def agent(tmp_path):
    cli = tmp_path / 'fake-codex'
    cli.write_text('''#!/usr/bin/env python3
import json, sys
from pathlib import Path
prompt = sys.stdin.read()
print(json.dumps({"type": "thread.started", "thread_id": "session-1"}), flush=True)
if prompt == "wait":
    import time
    time.sleep(60)
else:
    print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Сейчас посмотрю фото"}}))
    print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Запишу в журнал"}}))
    Path(sys.argv[sys.argv.index("--output-last-message") + 1]).write_text("Готово")
    print(json.dumps({"type": "turn.completed"}))
''')
    cli.chmod(0o755)
    return CodexAgent(Settings('secret', [1], tmp_path, engine='codex', codex_bin=str(cli)), None, None, None)


async def test_turn_resume_and_reset(agent):
    messages = []
    async def receive(text):
        messages.append(text)
    await agent.ask(1, 'hello', receive)
    assert messages == ['Готово']
    assert agent.info(1).turns == 1
    assert agent.info(1).session_id == 'session-1'
    assert agent._command(1)[-3:] == ['resume', 'session-1', '-']
    assert 'secret' not in ' '.join(agent._command(1))
    assert 'forced_login_method="chatgpt"' in agent._command(1)
    assert agent.store.path.name == 'codex-sessions.json'
    await agent.reset(1)
    assert agent.info(1).session_id is None


async def test_stop(agent):
    import asyncio
    async def receive(text):
        pass
    task = asyncio.create_task(agent.ask(1, 'wait', receive))
    for _ in range(100):
        if agent.store.get(1):
            break
        await asyncio.sleep(.01)
    assert await agent.interrupt(1)
    await asyncio.wait_for(task, 5)
    assert not agent.info(1).active


def test_bot_mcp_tools_are_explicitly_approved(agent):
    from trainer_bot.tools import TOOL_NAMES
    args = agent._command(1)
    config = dict(arg.split("=", 1) for arg in args if arg.startswith("mcp_servers."))
    assert json.loads(config["mcp_servers.tg.enabled_tools"]) == TOOL_NAMES
    assert json.loads(config["mcp_servers.tg.default_tools_approval_mode"]) == "prompt"
    for name in TOOL_NAMES:
        assert json.loads(config[f"mcp_servers.tg.tools.{name}.approval_mode"]) == "approve"
    agent.store.set(1, "existing-session")
    assert all(item in agent._command(1) for item in args[:-1])
