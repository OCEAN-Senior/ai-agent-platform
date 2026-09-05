from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from backend.app.core.config import settings

_ALLOWED_CALCULATOR_CHARS = set("0123456789+-*/(). ")


class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        func: Callable[..., Any],
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.func = func

    def to_ollama_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def _calculator(expression: str = "") -> str:
    if not expression or not all(ch in _ALLOWED_CALCULATOR_CHARS for ch in expression):
        return "Error: expression must contain only digits and + - * / ( ) . characters."
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as exc:
        return f"Error: {exc}"


def _get_current_time(**_: Any) -> str:
    return datetime.now(timezone.utc).isoformat()


async def _web_search(query: str = "", **_: Any) -> str:
    if not query:
        return "Error: query is required."
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{settings.SEARXNG_URL}/search",
                params={"q": query, "format": "json"},
            )
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        return f"Error: web search failed ({exc})"

    results = (data.get("results") or [])[:5]
    if not results:
        return "No results found."
    lines = [
        f"- {r.get('title', '')} ({r.get('url', '')}): {r.get('content', '')}"
        for r in results
    ]
    return "\n".join(lines)


CALCULATOR = Tool(
    name="calculator",
    description="Evaluate a basic arithmetic expression, e.g. '2 + 2 * 3'.",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The arithmetic expression to evaluate.",
            }
        },
        "required": ["expression"],
    },
    func=_calculator,
)

GET_CURRENT_TIME = Tool(
    name="get_current_time",
    description="Get the current date and time in UTC.",
    parameters={"type": "object", "properties": {}},
    func=_get_current_time,
)

WEB_SEARCH = Tool(
    name="web_search",
    description=(
        "Search the web for current information via a self-hosted, private "
        "search engine -- no third-party API key, nothing logged externally. "
        "Use for recent events or facts you're not confident about."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."}
        },
        "required": ["query"],
    },
    func=_web_search,
)

TOOL_REGISTRY: dict[str, Tool] = {
    CALCULATOR.name: CALCULATOR,
    GET_CURRENT_TIME.name: GET_CURRENT_TIME,
    WEB_SEARCH.name: WEB_SEARCH,
}
