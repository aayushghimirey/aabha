from dataclasses import dataclass, field
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Everything the API and the agent read from the environment.

    Required values are read with `os.environ`, so a missing one fails at
    import rather than halfway through a call.
    """

    DATABASE_URL: str = field(default_factory=lambda: os.environ["DATABASE_URL"])

    LIVEKIT_URL: str = field(default_factory=lambda: os.environ["LIVEKIT_URL"])
    LIVEKIT_API_KEY: str = field(default_factory=lambda: os.environ["LIVEKIT_API_KEY"])
    LIVEKIT_API_SECRET: str = field(
        default_factory=lambda: os.environ["LIVEKIT_API_SECRET"]
    )

    # How long an issued LiveKit access token stays usable.
    LIVEKIT_TOKEN_TTL_MINUTES: int = field(
        default_factory=lambda: int(os.getenv("LIVEKIT_TOKEN_TTL_MINUTES", "60"))
    )

    # LiveKit Inference model ids, so no per-provider plugin packages are
    # needed - the gateway resolves these and bills them through LiveKit.
    LLM_MODEL: str = field(
        default_factory=lambda: os.getenv("AABHA_LLM_MODEL", "openai/gpt-4.1-mini")
    )
    STT_MODEL: str = field(
        default_factory=lambda: os.getenv("AABHA_STT_MODEL", "deepgram/nova-3")
    )
    TTS_MODEL: str = field(
        default_factory=lambda: os.getenv("AABHA_TTS_MODEL", "cartesia/sonic-2")
    )

    GOOGLE_MAP_API_KEY: str = field(
        default_factory=lambda: os.getenv("GOOGLE_MAP_API_KEY", "")
    )


config = Config()
