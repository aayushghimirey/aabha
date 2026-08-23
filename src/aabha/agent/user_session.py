from dataclasses import dataclass

from aabha.models.conversation import Conversation
from aabha.models.user import User


@dataclass
class UserSession:
    """Per-job state, resolved before the agent starts and reachable from
    anywhere in the agent as `session.userdata`."""

    user: User
    conversation: Conversation
