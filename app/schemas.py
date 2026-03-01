from typing import Optional
from pydantic import BaseModel


class UserInfo(BaseModel):
    sub: str
    email: str
    email_verified: bool
    name: str
    given_name: str
    family_name: str
    picture: Optional[str] = None
