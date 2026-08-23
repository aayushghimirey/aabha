from pydantic import BaseModel


class TokenResponse(BaseModel):
    token: str
    server_url: str
    room: str
    identity: str
