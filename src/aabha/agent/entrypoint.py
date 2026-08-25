from __future__ import annotations

import logging
import os
from uuid import UUID

from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    cli,
    TurnHandlingOptions,
    inference,
    mcp,
)

from aabha.agent.assistant_agent import AssistantAgent
from aabha.agent.user_session import UserSession
from aabha.config import config
from aabha.db.pool import close_pool, open_pool
from aabha.db.repo.conversation_repo import create_conversation
from aabha.db.repo.user_repo import find_user_by_id
from aabha.services.agent_context import get_agent_context
from aabha.services.livekit_service import AGENT_NAME
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("aabha.agent")

# LiveKit Inference model ids, so no per-provider plugin packages are needed.
LLM_MODEL = os.getenv("AABHA_LLM_MODEL", "openai/gpt-4.1-mini")
STT_MODEL = os.getenv("AABHA_STT_MODEL", "deepgram/nova-3")
TTS_MODEL = os.getenv("AABHA_TTS_MODEL", "cartesia/sonic-2")

# `lk agent dev|start` discovers this by name; the __main__ block below keeps
# `python -m aabha.agent.worker` working too.
server = AgentServer()


# Named, so LiveKit only starts a job when the API explicitly dispatches one.
# Without the name, dispatch is automatic and fires on room creation - which a
# reconnect into a still-alive room never triggers.
@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: JobContext) -> None:
    await open_pool()

    agent: AssistantAgent | None = None

    async def shutdown() -> None:
        # Shutdown callbacks are gathered, not run in order, so the summary
        # write and the pool teardown have to be sequenced here - otherwise
        # the pool can close underneath the write.

        if agent is not None:
            await agent.finalise()

        await close_pool()

    ctx.add_shutdown_callback(shutdown)

    await ctx.connect()

    participant = await ctx.wait_for_participant()
    user_id = _identity_to_user_id(participant.identity)

    if user_id is None:
        ctx.shutdown(reason="participant identity is not a user id")
        return

    user = await find_user_by_id(user_id)

    if user is None:
        logger.warning("no such user: %s", user_id)
        ctx.shutdown(reason="unknown user")
        return

    # Resolved before the agent starts, so nothing that runs during the
    # conversation has to wait for it or handle it being missing.
    userdata = UserSession(user=user, conversation=await create_conversation(user.id))

    agent = AssistantAgent(chat_ctx=await get_agent_context(user.id))

    session = AgentSession[UserSession](
        userdata=userdata,
        llm=LLM_MODEL,
        stt=STT_MODEL,
        tts=TTS_MODEL,
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
        ),
        allow_interruptions=True,
        min_endpointing_delay=0.5,
        max_endpointing_delay=3.0,
        vad=inference.VAD(model="silero", activation_threshold=0.5),
        tools=[
            mcp.MCPToolset(
                id="tavily", mcp_server=mcp.MCPServerHTTP(url=config.TAVILY_MCP_URL)
            )
        ],
    )

    logger.info(
        "starting conversation %s for %s", userdata.conversation.id, user.username
    )

    await session.start(agent, room=ctx.room)


def _identity_to_user_id(identity: str) -> UUID | None:
    """Tokens are minted with the user id as the identity (see livekit_service),
    but anyone can join a room with an identity of their choosing."""
    try:
        return UUID(identity)
    except ValueError:
        logger.warning("participant identity is not a uuid: %r", identity)
        return None


if __name__ == "__main__":
    cli.run_app(server)
