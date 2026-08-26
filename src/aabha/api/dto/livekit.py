from pydantic import BaseModel


class LiveKitTokenResponse(BaseModel):
    """Everything a client needs to open a LiveKit connection."""

    token: str
    server_url: str
    room: str
    identity: str
