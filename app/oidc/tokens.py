import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AccessToken, AuthCode, SigningKey, User
from app.security import base_claims_for_user, sign_jwt


def get_active_key(db: Session) -> SigningKey:
    key = db.query(SigningKey).filter(SigningKey.is_active.is_(True)).first()
    if not key:
        raise ValueError("No active signing key configured")
    return key


def build_id_token(db: Session, user: User, auth_code: AuthCode) -> str:
    settings = get_settings()
    key = get_active_key(db)
    claims = {
        "aud": auth_code.client_id,
        "sub": user.sub,
        "nonce": auth_code.nonce,
        **base_claims_for_user(user),
    }
    return sign_jwt(claims, key, settings.id_token_ttl_seconds)


def build_access_token(db: Session, user: User, auth_code: AuthCode, expires_at: datetime) -> str:
    settings = get_settings()
    key = get_active_key(db)
    jti = secrets.token_hex(16)
    token_row = AccessToken(
        jti=jti,
        client_id=auth_code.client_id,
        user_id=user.id,
        scope=auth_code.scope,
        expires_at=expires_at,
    )
    db.add(token_row)
    db.flush()

    claims = {
        "sub": user.sub,
        "aud": auth_code.client_id,
        "scope": auth_code.scope,
        "jti": jti,
        **base_claims_for_user(user),
    }
    return sign_jwt(claims, key, settings.access_token_ttl_seconds)
