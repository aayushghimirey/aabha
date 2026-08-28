from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CoreEntity(BaseModel):
    """What every row carries. Kept in one place so a repo never has to decide
    for itself what a stored thing looks like."""

    id: UUID

    created_at: datetime
    updated_at: datetime | None = None


class User(CoreEntity):
    """A row from users.

    Carries the password hash, so it must never be handed back from a route -
    api/schemas.py has UserResponse for that.
    """

    username: str
    email: EmailStr
    password_hash: str
    dob: date


MemoryKind = Literal["preference", "habit", "fact"]

MemorySource = Literal["user", "agent", "conversation", "system"]


class MemoryDraft(BaseModel):
    """A memory before it is a row - everything a writer supplies. Kept apart
    from Memory so writing one does not mean inventing an id and a created_at."""

    key: str = Field(
        min_length=1,
        max_length=64,
        description="Short stable handle, such as coffee_order or commute."
        " Saving under a key that is taken overwrites it.",
    )

    kind: MemoryKind = "fact"

    content: str = Field(
        min_length=1, max_length=2000, description="The actual memory content"
    )

    source: MemorySource = "conversation"

    importance: int = Field(
        default=5, ge=1, le=10, description="How important this memory is"
    )


class Memory(CoreEntity, MemoryDraft):
    user_id: UUID


class Conversation(CoreEntity):
    """One call. The summary is written when it ends, so it is NULL for a call
    still running or one that was cut off before it could be written up."""

    user_id: UUID
    message_count: int = 0
    summary: str | None = None
