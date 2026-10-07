import json
import re
from collections.abc import AsyncIterator
from typing import Any

import httpx

from backend.app.core.config import settings
from backend.app.services.llm.base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """Talks to any OpenAI-compatible /v1 endpoint (e.g. an OmniRoute gateway).

    The rest of the app speaks Ollama's message shape (tool-call arguments as a dict,
    tool results without ids), so this provider translates in both directions and
    agents like ToolAgent work unchanged whichever provider is configured.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        model_prefix: str | None = None,
        max_tokens: int | None = None,
    ):
        self.base_url = (base_url or settings.OPENAI_COMPAT_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.OPENAI_COMPAT_API_KEY
        # Model names stay as in OLLAMA_MODEL / OLLAMA_CODER_MODEL; the gateway's
        # routing prefix (e.g. "ollama/") is added here.
        prefix = settings.OPENAI_COMPAT_MODEL_PREFIX if model_prefix is None else model_prefix
        self.model = prefix + (model or settings.OLLAMA_MODEL)
        self.max_tokens = max_tokens

    async def chat(self, message: str, history: list[dict[str, str]] | None = None) -> str:
        messages = [*(history or []), {"role": "user", "content": message}]
        message_response = await self._chat_request(messages)
        return message_response["content"]

    async def chat_with_tools(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return await self._chat_request(messages, tools=tools)

    async def chat_stream(
        self, message: str, history: list[dict[str, str]] | None = None
    ) -> AsyncIterator[str]:
        messages = [*(history or []), {"role": "user", "content": message}]
        payload = {"model": self.model, "messages": messages, "stream": True, **self._limits()}
        think_filter = ThinkFilter()

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{self.base_url}/chat/completions", json=payload, headers=self._headers()
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    # Server-sent events: "data: {...}" lines, terminated by "data: [DONE]".
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    choices = json.loads(data).get("choices") or []
                    content = (choices[0].get("delta") or {}).get("content") if choices else None
                    visible = think_filter.feed(content) if content else ""
                    if visible:
                        yield visible
                tail = think_filter.flush()
                if tail:
                    yield tail

    async def _chat_request(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": _to_openai_messages(messages),
            "stream": False,
            **self._limits(),
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            result = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=self._headers()
            )
            result.raise_for_status()
            return _to_ollama_message(result.json()["choices"][0]["message"])

    def _limits(self) -> dict[str, int]:
        return {"max_tokens": self.max_tokens} if self.max_tokens else {}

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}


def _to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Ollama-shaped history to OpenAI shape.

    OpenAI requires each tool call to carry an id, its arguments as a JSON string, and
    each tool result to reference that id. Ollama has none of this, so ids are filled
    in and tool results are matched to the preceding assistant's calls in order.
    """
    converted: list[dict[str, Any]] = []
    pending_ids: list[str] = []
    for index, msg in enumerate(messages):
        msg = dict(msg)
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            calls = []
            for call_index, call in enumerate(msg["tool_calls"]):
                fn = call["function"]
                arguments = fn.get("arguments") or {}
                calls.append({
                    "id": call.get("id") or f"call_{index}_{call_index}",
                    "type": "function",
                    "function": {
                        "name": fn["name"],
                        "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments),
                    },
                })
            msg["tool_calls"] = calls
            msg["content"] = msg.get("content") or ""
            pending_ids = [call["id"] for call in calls]
        elif msg.get("role") == "tool" and "tool_call_id" not in msg:
            msg["tool_call_id"] = pending_ids.pop(0) if pending_ids else f"call_{index}"
        converted.append(msg)
    return converted


def _to_ollama_message(message: dict[str, Any]) -> dict[str, Any]:
    """Convert an OpenAI assistant message back to the Ollama shape agents expect."""
    result: dict[str, Any] = {"role": "assistant", "content": strip_think(message.get("content") or "")}
    tool_calls = []
    for call in message.get("tool_calls") or []:
        fn = call.get("function") or {}
        raw_args = fn.get("arguments") or "{}"
        try:
            arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            arguments = {}
        tool_calls.append({"id": call.get("id"), "function": {"name": fn.get("name"), "arguments": arguments}})
    if tool_calls:
        result["tool_calls"] = tool_calls
    return result


_THINK_BLOCK = re.compile(r"<think>.*?(?:</think>|\Z)", re.S)


def strip_think(text: str) -> str:
    """Remove reasoning-model <think>...</think> blocks (also an unterminated one at the end)."""
    return _THINK_BLOCK.sub("", text).strip()


class ThinkFilter:
    """Streaming counterpart of strip_think: drops text inside <think>...</think> across chunks."""

    def __init__(self) -> None:
        self._buffer = ""
        self._inside = False
        self._started = False

    def feed(self, chunk: str) -> str:
        self._buffer += chunk
        out = []
        while True:
            tag = "</think>" if self._inside else "<think>"
            idx = self._buffer.find(tag)
            if idx == -1:
                # Keep a possible partial tag at the end for the next chunk.
                keep = len(tag) - 1
                safe, self._buffer = self._buffer[:-keep] if len(self._buffer) > keep else "", self._buffer[-keep:]
                if not self._inside:
                    out.append(safe)
                break
            if not self._inside:
                out.append(self._buffer[:idx])
            self._buffer = self._buffer[idx + len(tag):]
            self._inside = not self._inside
        return self._lstrip_once("".join(out))

    def flush(self) -> str:
        rest, self._buffer = ("" if self._inside else self._buffer), ""
        return self._lstrip_once(rest)

    def _lstrip_once(self, text: str) -> str:
        # Reasoning models put blank lines after </think>; drop leading whitespace of the answer.
        if not self._started:
            text = text.lstrip()
            self._started = bool(text)
        return text
