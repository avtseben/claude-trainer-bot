"""Check the real bot MCP transport without calling a model or sending messages."""
import asyncio
import sys
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .config import load_settings
from .tools import TOOL_NAMES


async def main():
    settings = load_settings()
    params = StdioServerParameters(
        command=sys.executable,
        args=['-m', 'trainer_bot.codex_tools', str(settings.owner_chat_id)],
        cwd=str(settings.workspace),
        env={'TRAINER_WORKSPACE': str(settings.workspace),
             'TELEGRAM_BOT_TOKEN': settings.telegram_token,
             'RENDER_WIDTH': str(settings.render_width)},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
            await session.initialize()
            result = await session.list_tools()
            names = {tool.name for tool in result.tools}
            if names != set(TOOL_NAMES):
                raise RuntimeError(f'Unexpected tool catalog: {sorted(names)}')
            print('MCP OK: ' + ', '.join(sorted(names)))


if __name__ == '__main__':
    asyncio.run(main())
