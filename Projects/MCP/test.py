from fastmcp import FastMCP

mcp = FastMCP("MyFreeMCP")

@mcp.tool()
async def echo(text: str) -> str:
    return f"Echo: {text}"

if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run_async())