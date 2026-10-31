"""Exercise the real stdio server from a workspace outside the source checkout."""
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from trainer_bot.tools import TOOL_NAMES


async def test_stdio_handshake_and_tool_call(tmp_path):
    params = StdioServerParameters(
        command=sys.executable,
        args=['-m', 'trainer_bot.codex_tools', '123'],
        cwd=str(tmp_path),
        env={'TRAINER_WORKSPACE': str(tmp_path), 'TELEGRAM_BOT_TOKEN': '123456:TEST_TOKEN'},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            assert {t.name for t in result.tools} == set(TOOL_NAMES)
            result = await session.call_tool('send_artifact', {'path': 'missing.html'})
            assert result.isError
            assert 'Файл не найден' in result.content[0].text
