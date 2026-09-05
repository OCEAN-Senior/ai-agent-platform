class ConversationMemory:
    """In-process, non-persistent short-term memory for a chat session.

    Cleared on server restart. Long-term, persistent memory is a separate
    concern that will build on the Vector DB / RAG milestone.
    """

    def __init__(self, max_messages: int = 20) -> None:
        self._max_messages = max_messages
        self._store: dict[str, list[dict[str, str]]] = {}

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        return list(self._store.get(session_id, []))

    def add_exchange(self, session_id: str, user_message: str, assistant_message: str) -> None:
        history = self._store.setdefault(session_id, [])
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": assistant_message})
        if len(history) > self._max_messages:
            del history[: len(history) - self._max_messages]

    def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)
