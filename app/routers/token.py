import json
import base64
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Header, HTTPException
from jose import jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AccessToken, AuthCode, OAuthClient, User
from app.oidc.tokens import build_access_token, build_id_token, get_active_key
from app.schemas import UserInfo
from app.security import now_utc, verify_client_secret, verify_pkce_s256

router = APIRouter()


def _parse_basic_auth(header: str | None) -> tuple[str, str] | None:
    if not header or not header.lower().startswith("basic "):
        return None
    decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
    client_id, client_secret = decoded.split(":", 1)
    return client_id, client_secret


@router.post("/token")
def token(
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    client_id: str | None = Form(None),
    code_verifier: str = Form(...),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail={"error": "unsupported_grant_type"})

    auth_code = db.query(AuthCode).filter_by(code=code).first()
    if not auth_code or auth_code.consumed_at is not None or auth_code.expires_at < now_utc():
        raise HTTPException(status_code=400, detail={"error": "invalid_grant"})
    if redirect_uri != auth_code.redirect_uri:
        raise HTTPException(status_code=400, detail={"error": "invalid_grant", "error_description": "redirect_uri mismatch"})
    if auth_code.code_challenge_method != "S256" or not verify_pkce_s256(code_verifier, auth_code.code_challenge):
        raise HTTPException(status_code=400, detail={"error": "invalid_grant", "error_description": "PKCE verification failed"})

    client = db.query(OAuthClient).filter_by(client_id=auth_code.client_id).first()
    if not client:
        raise HTTPException(status_code=400, detail={"error": "invalid_client"})

    basic = _parse_basic_auth(authorization)
    if client.is_confidential:
        if not basic:
            raise HTTPException(status_code=401, detail={"error": "invalid_client"})
        basic_client_id, secret = basic
        if basic_client_id != client.client_id or not verify_client_secret(secret, client.client_secret_hash):
            raise HTTPException(status_code=401, detail={"error": "invalid_client"})
    else:
        if basic:
            raise HTTPException(status_code=400, detail={"error": "invalid_request", "error_description": "public clients must use auth method none"})
        if client_id != client.client_id:
            raise HTTPException(status_code=400, detail={"error": "invalid_client"})

    user = db.query(User).filter_by(id=auth_code.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail={"error": "invalid_grant"})

    expires_at = datetime.utcnow() + timedelta(seconds=get_settings().access_token_ttl_seconds)
    access_token = build_access_token(db, user, auth_code, expires_at)
    id_token = build_id_token(db, user, auth_code)
    auth_code.consumed_at = now_utc()
    db.commit()
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": get_settings().access_token_ttl_seconds,
        "id_token": id_token,
        "scope": auth_code.scope,
    }


@router.get("/userinfo", response_model=UserInfo)
def userinfo(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"error": "invalid_token"})
    token = authorization.split(" ", 1)[1]
    key = get_active_key(db)
    issuer = str(get_settings().issuer).rstrip("/")
    try:
        claims = jwt.decode(token, json.loads(key.public_jwk), algorithms=["RS256"], issuer=issuer, options={"verify_aud": False})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail={"error": "invalid_token", "error_description": str(exc)}) from exc

    jti = claims.get("jti")
    if not jti:
        raise HTTPException(status_code=401, detail={"error": "invalid_token"})
    token_row = db.query(AccessToken).filter_by(jti=jti).first()
    if not token_row or token_row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail={"error": "invalid_token"})
    user = db.query(User).filter_by(id=token_row.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail={"error": "invalid_token"})
    return UserInfo(
        sub=user.sub,
        email=user.email,
        email_verified=user.email_verified,
        name=user.name,
        given_name=user.given_name,
        family_name=user.family_name,
        picture=user.picture,
    )
