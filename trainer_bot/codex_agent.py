"""Codex CLI backend using ChatGPT subscription authentication and JSONL events."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import tempfile
from pathlib import Path
from dataclasses import dataclass, field

from .agent import SessionInfo, SessionStore, TELEGRAM_CONTEXT
from .tools import TOOL_NAMES


log = logging.getLogger(__name__)


@dataclass
class CodexState:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    process: asyncio.subprocess.Process | None = None
    turns: int = 0
    stopped: bool = False


class CodexAgent:
    def __init__(self, settings, bot, renderer, exercises):
        self.settings = settings
        self.store = SessionStore(settings.state_dir / "codex-sessions.json")
        self._chats: dict[int, CodexState] = {}

    def _command(self, chat_id):
        # A dedicated CODEX_HOME is recommended. Never fall back to API billing.
        config = {
            "forced_login_method": "chatgpt",
            "model_provider": "openai",
            "approval_policy": "never",
            "sandbox_mode": "workspace-write",
            "mcp_servers.tg.command": sys.executable,
            "mcp_servers.tg.required": True,
            "mcp_servers.tg.startup_timeout_sec": 60,
            "mcp_servers.tg.tool_timeout_sec": 120,
            "mcp_servers.tg.enabled_tools": TOOL_NAMES,
            # Only the bot-owned tools are preapproved; unknown tools stay unavailable.
            "mcp_servers.tg.default_tools_approval_mode": "prompt",
            "mcp_servers.tg.args": ["-m", "trainer_bot.codex_tools", str(chat_id)],
            "mcp_servers.tg.env.TRAINER_WORKSPACE": str(self.settings.workspace),
            "mcp_servers.tg.env_vars": ["TELEGRAM_BOT_TOKEN"],
            "mcp_servers.tg.env.RENDER_WIDTH": str(self.settings.render_width),
            "developer_instructions": TELEGRAM_CONTEXT + "\nПрочитай CLAUDE.md в рабочей папке и следуй правилам тренера.",
        }
        for name in TOOL_NAMES:
            config[f"mcp_servers.tg.tools.{name}.approval_mode"] = "approve"
        if self.settings.codex_reasoning_effort:
            config["model_reasoning_effort"] = self.settings.codex_reasoning_effort
        args = [self.settings.codex_bin, "exec", "--ignore-user-config", "--json", "--skip-git-repo-check"]
        for key, value in config.items():
            args.extend(["-c", f"{key}={json.dumps(value, ensure_ascii=False)}"])
        if self.settings.model:
            args.extend(["--model", self.settings.model])
        session = self.store.get(chat_id)
        if session:
            args.extend(["resume", session])
        args.append("-")
        return args

    async def ask(self, chat_id, prompt, on_text):
        state = self._chats.setdefault(chat_id, CodexState())
        async with state.lock:
            state.stopped = False
            env = os.environ.copy()
            # Also pass settings loaded from .env to the MCP child without logging them.
            env.pop("OPENAI_API_KEY", None)
            env["TELEGRAM_BOT_TOKEN"] = self.settings.telegram_token
            output_dir = tempfile.TemporaryDirectory(prefix="trainer-codex-")
            output_path = Path(output_dir.name) / "final.txt"
            command = self._command(chat_id)
            command[2:2] = ["--output-last-message", str(output_path)]
            process = await asyncio.create_subprocess_exec(
                *command, cwd=self.settings.workspace, env=env,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE, start_new_session=True,
                limit=32 * 1024 * 1024,
            )
            state.process = process
            stderr_task = asyncio.create_task(self._log_stderr(process))
            failed = False
            try:
                process.stdin.write(prompt.encode())
                await process.stdin.drain()
                process.stdin.close()
                async for line in process.stdout:
                    event = json.loads(line)
                    kind = event.get("type")
                    if kind == "thread.started":
                        self.store.set(chat_id, event["thread_id"])
                    elif kind == "turn.completed":
                        state.turns += 1
                    elif kind in {"turn.failed", "error"}:
                        failed = True
                code = await process.wait()
                if not state.stopped and (code or failed):
                    raise RuntimeError("Codex не завершил ход. Проверьте codex login status, лимиты подписки и /new.")
                if not state.stopped and output_path.exists():
                    final_text = output_path.read_text().strip()
                    if final_text:
                        await on_text(final_text)
            finally:
                output_dir.cleanup()
                await self._terminate(state)
                await stderr_task
                state.process = None

    async def _log_stderr(self, process):
        async for line in process.stderr:
            text = line.decode(errors="replace").strip()
            for secret in (self.settings.telegram_token, os.environ.get("OPENAI_API_KEY"),
                           os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"), os.environ.get("ANTHROPIC_API_KEY")):
                if secret:
                    text = text.replace(secret, "[REDACTED]")
            if text:
                log.warning("Codex CLI: %s", text[:4000])

    async def _terminate(self, state):
        process = state.process
        if process is None or process.returncode is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(process.wait(), 5)
        except asyncio.TimeoutError:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await process.wait()

    async def interrupt(self, chat_id):
        state = self._chats.get(chat_id)
        if state is None or state.process is None:
            return False
        state.stopped = True
        await self._terminate(state)
        return True

    async def reset(self, chat_id):
        state = self._chats.get(chat_id)
        if state:
            await self.interrupt(chat_id)
            async with state.lock:
                self.store.drop(chat_id)
                state.turns = 0
        else:
            self.store.drop(chat_id)

    def info(self, chat_id):
        state = self._chats.get(chat_id)
        return SessionInfo(self.store.get(chat_id), bool(state and state.process), 0.0, state.turns if state else 0)

    async def close(self):
        for chat_id in list(self._chats):
            await self.interrupt(chat_id)
