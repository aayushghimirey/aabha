from __future__ import annotations

import logging
from uuid import UUID

from livekit.agents import (
    AgentServer,
    AgentSession,
    ChatContext,
    JobContext,
    TurnHandlingOptions,
    cli,
    inference,
)

from aabha.agent.agent import AabhaAgent
from aabha.config import config
from aabha.db.conn_pool import close_connection_pool, open_connection_pool
from aabha.db.repo.user_repo import find_user_by_id
from aabha.service.conversation_service import UserConversation
from aabha.service.livekit_service import AGENT_NAME
from aabha.service.location_service import UserLocation
from aabha.service.memory_service import UserMemory

logger = logging.getLogger("aabha.agent")

server = AgentServer()


async def build_agent_context(
    memory: UserMemory, conversation: UserConversation
) -> ChatContext:
    """What the agent starts the call knowing: what is remembered about the
    user, and notes from the calls before this one. Empty when there is nothing
    of either yet - a first call, not an error.

    The conversation row for this call is already open by now, so recall leaves
    it out rather than handing the agent an empty summary of itself."""
    chat_ctx = ChatContext.empty()

    memories = await memory.recall()
    conversations = await conversation.recall()

    if memories is not None:
        chat_ctx.add_message(role="system", content=memories)

    if conversations is not None:
        chat_ctx.add_message(role="system", content=conversations)

    return chat_ctx


def identity_to_user_id(identity: str) -> UUID | None:
    """Tokens are minted with the user id as the identity (see
    livekit_service), but anyone can join a room with an identity of their
    choosing."""
    try:
        return UUID(identity)
    except ValueError:
        logger.warning("participant identity is not a uuid: %r", identity)
        return None


# Named, so LiveKit only starts a job when the API explicitly dispatches one.
# Without the name, dispatch is automatic and fires on room creation - which a
# reconnect into a still-alive room never triggers.
@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: JobContext) -> None:
    await open_connection_pool()

    agent: AabhaAgent | None = None

    async def shutdown() -> None:
        # Shutdown callbacks are gathered rather than run in order, so the
        # summary write and the pool teardown have to be sequenced here -
        # otherwise the pool can close underneath the write.
        if agent is not None:
            await agent.summarise()

        await close_connection_pool()

    ctx.add_shutdown_callback(shutdown)

    await ctx.connect()

    participant = await ctx.wait_for_participant()
    user_id = identity_to_user_id(participant.identity)

    if user_id is None:
        ctx.shutdown(reason="participant identity is not a user id")
        return

    user = await find_user_by_id(user_id)

    if user is None:
        logger.warning("no such user: %s", user_id)
        ctx.shutdown(reason="unknown user")
        return

    # All resolved before the agent starts, so nothing during the call has to
    # wait for them or handle them being missing.
    memory = UserMemory(user.id)
    conversation = UserConversation(user.id)
    location = UserLocation(participant.identity)

    await conversation.create_conversation()

    agent = AabhaAgent(
        memory=memory,
        conversation=conversation,
        location=location,
        chat_ctx=await build_agent_context(memory, conversation),
    )

    session = AgentSession(
        llm=config.LLM_MODEL,
        stt=config.STT_MODEL,
        tts=config.TTS_MODEL,
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
        ),
        allow_interruptions=True,
        min_endpointing_delay=0.5,
        max_endpointing_delay=3.0,
        vad=inference.VAD(model="silero", activation_threshold=0.6),
    )

    logger.info(
        "starting conversation %s for %s", conversation.conversation_id, user.username
    )

    await session.start(agent, room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)
