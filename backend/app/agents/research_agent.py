import logging

from backend.app.agents.base import AgentInput, AgentResult, BaseAgent
from backend.app.services.chat_service import get_chat_response
from backend.app.services.rag.rag_service import retrieve_context

logger = logging.getLogger("ai_agent_platform.research_agent")

RESEARCH_PROMPT_WITH_CONTEXT = (
    "You are a research assistant. Use the context below if it is relevant "
    "to the question. If the context does not answer the question, say so "
    "and answer from your own knowledge instead. Respond in the same "
    "language as the question.\n\nContext:\n{context}\n\nQuestion: {task}"
)

RESEARCH_PROMPT_NO_CONTEXT = (
    "You are a research assistant. Answer the following question with the "
    "most accurate, well-structured information you have. If you are not "
    "certain about a fact, say so explicitly instead of guessing. Respond "
    "in the same language as the question.\n\nQuestion: {task}"
)


class ResearchAgent(BaseAgent):
    name = "research_agent"

    async def run(self, agent_input: AgentInput) -> AgentResult:
        try:
            context_chunks = await retrieve_context(agent_input.task)
        except Exception:
            logger.warning("RAG retrieval failed, falling back to knowledge-only", exc_info=True)
            context_chunks = []

        if context_chunks:
            prompt = RESEARCH_PROMPT_WITH_CONTEXT.format(
                context="\n---\n".join(context_chunks), task=agent_input.task
            )
            source = "rag"
        else:
            prompt = RESEARCH_PROMPT_NO_CONTEXT.format(task=agent_input.task)
            source = "llm_knowledge_only"

        output = await get_chat_response(prompt)
        return AgentResult(output=output, metadata={"source": source})
