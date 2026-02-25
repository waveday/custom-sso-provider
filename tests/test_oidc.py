import base64
import hashlib
import secrets

from app.cli import rotate_key
from app.db import SessionLocal
from app.models import OAuthClient, User
from app.security import hash_client_secret, hash_password


def _pkce_pair():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


def setup_seed(confidential: bool = True):
    rotate_key(make_active=True)
    db = SessionLocal()
    user = User(
        sub="sub123",
        email="user@example.com",
        email_verified=True,
        name="Test User",
        given_name="Test",
        family_name="User",
        picture="https://example.com/u.png",
        password_hash=hash_password("pass123"),
    )
    client = OAuthClient(
        client_id="client123",
        client_secret_hash=hash_client_secret("secret123") if confidential else None,
        client_name="My Client",
        redirect_uris="http://localhost:9999/callback",
        is_confidential=confidential,
    )
    db.add(user)
    db.add(client)
    db.commit()
    db.close()


def _auth_code_flow(client, confidential=True):
    setup_seed(confidential=confidential)
    verifier, challenge = _pkce_pair()
    params = {
        "client_id": "client123",
        "redirect_uri": "http://localhost:9999/callback",
        "response_type": "code",
        "scope": "openid profile email",
        "state": "state123",
        "nonce": "nonce123",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }

    r = client.get("/authorize", params=params, follow_redirects=False)
    assert r.status_code == 302
    r = client.post("/login", data={"email": "user@example.com", "password": "pass123"}, follow_redirects=False)
    assert r.status_code == 302
    r = client.post("/authorize/approve", follow_redirects=False)
    assert r.status_code == 302
    location = r.headers["location"]
    code = location.split("code=")[1].split("&")[0]

    if confidential:
        basic = base64.b64encode(b"client123:secret123").decode()
        token_resp = client.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "http://localhost:9999/callback",
                "code_verifier": verifier,
            },
            headers={"Authorization": f"Basic {basic}"},
        )
    else:
        token_resp = client.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "client_id": "client123",
                "code": code,
                "redirect_uri": "http://localhost:9999/callback",
                "code_verifier": verifier,
            },
        )
    return token_resp


def test_discovery_and_jwks(client):
    setup_seed()
    d = client.get("/.well-known/openid-configuration")
    assert d.status_code == 200
    assert d.json()["authorization_endpoint"].endswith("/authorize")
    jwks = client.get("/jwks.json")
    assert jwks.status_code == 200
    assert len(jwks.json()["keys"]) == 1


def test_confidential_token_exchange_and_userinfo(client):
    token = _auth_code_flow(client, confidential=True)
    assert token.status_code == 200
    payload = token.json()
    assert "id_token" in payload
    userinfo = client.get("/userinfo", headers={"Authorization": f"Bearer {payload['access_token']}"})
    assert userinfo.status_code == 200
    assert userinfo.json()["email"] == "user@example.com"


def test_public_client_pkce_exchange(client):
    token = _auth_code_flow(client, confidential=False)
    assert token.status_code == 200
    assert token.json()["token_type"] == "Bearer"
