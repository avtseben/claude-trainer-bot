"""Private stdio MCP server; each process is bound to one Telegram chat."""
import asyncio
import os
import sys
from pathlib import Path

from aiogram import Bot
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

from .exercises import ExerciseDb
from .render import Renderer
from .tools import build_tools


async def main():
    workspace = Path(os.environ["TRAINER_WORKSPACE"]).resolve()
    bot = Bot(os.environ["TELEGRAM_BOT_TOKEN"])
    renderer = Renderer(width=int(os.environ.get("RENDER_WIDTH", "800")))
    definitions = build_tools(int(sys.argv[1]), bot, workspace, renderer, ExerciseDb(workspace / "exercises-db"))
    handlers = {tool.name: tool for tool in definitions}
    server = Server("tg")

    @server.list_tools()
    async def list_tools():
        return [Tool(name=t.name, description=t.description, inputSchema=t.input_schema) for t in definitions]

    @server.call_tool()
    async def call_tool(name, arguments):
        result = await handlers[name].handler(arguments)
        return CallToolResult(content=[TextContent(**item) for item in result["content"]],
                              isError=result.get("is_error", False))

    try:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    finally:
        await renderer.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
