from datetime import datetime, timezone
from typing import Any, Callable

_ALLOWED_CALCULATOR_CHARS = set("0123456789+-*/(). ")


class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        func: Callable[..., str],
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

TOOL_REGISTRY: dict[str, Tool] = {
    CALCULATOR.name: CALCULATOR,
    GET_CURRENT_TIME.name: GET_CURRENT_TIME,
}
