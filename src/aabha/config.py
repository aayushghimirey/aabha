from dataclasses import dataclass, field
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
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

    TAVILY_MCP_URL: str = field(default_factory=lambda: os.environ["TAVILY_MCP_URL"])

    # Turns the coordinates a browser reports into a place name. The public
    # instance is rate limited to a request a second; set this to your own
    # Nominatim if that ever bites.
    NOMINATIM_URL: str = field(
        default_factory=lambda: os.getenv(
            "NOMINATIM_URL"
        )
    )


config = Config()
