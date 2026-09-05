from mcp.server.mcpserver import MCPServer

server = MCPServer("example-tools")


@server.tool()
def word_count(text: str) -> int:
    """Count the number of words in the given text."""
    return len(text.split())


@server.tool()
def reverse_text(text: str) -> str:
    """Reverse the given text."""
    return text[::-1]


if __name__ == "__main__":
    server.run()
