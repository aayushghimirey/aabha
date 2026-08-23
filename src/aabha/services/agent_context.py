from uuid import UUID

from aabha.db.repo.memory_repo import get_memories
from aabha.db.repo.conversation_repo import get_conversations
from aabha.models.memory import Memory
from aabha.models.conversation import Conversation
from livekit.agents import ChatContext


async def build_agent_context(user_id: UUID) -> list[tuple[str, str]]:
    memories: list[Memory] = await get_memories(user_id, limit=50)
    conversations: list[Conversation] = await get_conversations(user_id, 5)

    context = []

    if memories:
        memory_text = "\n".join(f"- {mem.content}" for mem in memories)

        context.append(
            (
                "system",
                f"Relevant memories about the user:\n{memory_text}",
            )
        )

    if conversations:
        conversation_text = "\n".join(
            f"- {conv.summary}" for conv in conversations if conv.summary
        )

        if conversation_text:
            context.append(
                (
                    "system",
                    f"Previous conversation summaries:\n{conversation_text}",
                )
            )

    return context


async def get_agent_context(user_id: UUID) -> ChatContext:
    context = await build_agent_context(user_id)

    chat_ctx = ChatContext.empty()

    for role, content in context:
        chat_ctx.add_message(
            role=role,
            content=content,
        )

    return chat_ctx
