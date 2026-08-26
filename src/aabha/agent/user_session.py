from dataclasses import dataclass

from aabha.db.model.conversation import Conversation
from aabha.db.model.user import User


@dataclass
class UserSession:
    user: User
    conversation: Conversation
