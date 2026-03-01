import json
import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.models import SigningKey, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def hash_client_secret(secret: str) -> str:
    return pwd_context.hash(secret)


def verify_client_secret(secret: str, secret_hash: Optional[str]) -> bool:
    if not secret_hash:
        return False
    return pwd_context.verify(secret, secret_hash)


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def make_auth_code() -> str:
    return secrets.token_urlsafe(32)


def make_session_token() -> str:
    return secrets.token_urlsafe(32)


def verify_pkce_s256(verifier: str, challenge: str) -> bool:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return secrets.compare_digest(encoded, challenge)


def sign_jwt(claims: dict, key: SigningKey, ttl_seconds: int) -> str:
    settings = get_settings()
    iat = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "iss": str(settings.issuer).rstrip("/"),
        "iat": iat,
        "exp": iat + ttl_seconds,
        **claims,
    }
    headers = {"kid": key.kid, "alg": "RS256", "typ": "JWT"}
    return jwt.encode(payload, json.loads(key.private_jwk), algorithm="RS256", headers=headers)


def base_claims_for_user(user: User) -> dict:
    return {
        "sub": user.sub,
        "email": user.email,
        "email_verified": user.email_verified,
        "name": user.name,
        "given_name": user.given_name,
        "family_name": user.family_name,
        "picture": user.picture,
    }


def expiry_from_now(seconds: int) -> datetime:
    return now_utc() + timedelta(seconds=seconds)
