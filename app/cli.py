import json
import secrets
from typing import Optional

import typer
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose.utils import base64url_encode

from app.db import SessionLocal
from app.models import OAuthClient, SigningKey, User
from app.security import hash_client_secret, hash_password

app = typer.Typer(help="OIDC provider bootstrap CLI")


def _int_to_b64(n: int) -> str:
    byte_len = (n.bit_length() + 7) // 8
    return base64url_encode(n.to_bytes(byte_len, "big")).decode("utf-8")


@app.command("create-user")
def create_user(
    email: str,
    password: str,
    name: str,
    given_name: str,
    family_name: str,
    picture: Optional[str] = None,
):
    db = SessionLocal()
    try:
        sub = secrets.token_hex(16)
        user = User(
            sub=sub,
            email=email,
            name=name,
            given_name=given_name,
            family_name=family_name,
            picture=picture,
            password_hash=hash_password(password),
            email_verified=True,
        )
        db.add(user)
        db.commit()
        typer.echo(f"created user {email} sub={sub}")
    finally:
        db.close()


@app.command("create-client")
def create_client(
    client_name: str,
    redirect_uri: list[str] = typer.Option(..., "--redirect-uri"),
    public: bool = typer.Option(False, help="Set true for public clients"),
):
    db = SessionLocal()
    try:
        client_id = secrets.token_urlsafe(24)
        secret_plain = None if public else secrets.token_urlsafe(32)
        client = OAuthClient(
            client_id=client_id,
            client_secret_hash=None if public else hash_client_secret(secret_plain),
            client_name=client_name,
            redirect_uris=" ".join(redirect_uri),
            is_confidential=not public,
        )
        db.add(client)
        db.commit()
        typer.echo(f"client_id={client_id}")
        if secret_plain:
            typer.echo(f"client_secret={secret_plain}")
    finally:
        db.close()


@app.command("rotate-key")
def rotate_key(make_active: bool = True):
    db = SessionLocal()
    try:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        numbers = private_key.private_numbers()
        public_numbers = numbers.public_numbers
        kid = secrets.token_hex(8)

        private_jwk = {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": kid,
            "n": _int_to_b64(public_numbers.n),
            "e": _int_to_b64(public_numbers.e),
            "d": _int_to_b64(numbers.d),
            "p": _int_to_b64(numbers.p),
            "q": _int_to_b64(numbers.q),
            "dp": _int_to_b64(numbers.dmp1),
            "dq": _int_to_b64(numbers.dmq1),
            "qi": _int_to_b64(numbers.iqmp),
        }
        public_jwk = {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": kid,
            "n": _int_to_b64(public_numbers.n),
            "e": _int_to_b64(public_numbers.e),
        }

        if make_active:
            for key in db.query(SigningKey).all():
                key.is_active = False

        row = SigningKey(
            kid=kid,
            private_jwk=json.dumps(private_jwk),
            public_jwk=json.dumps(public_jwk),
            is_active=make_active,
            algorithm="RS256",
        )
        db.add(row)
        db.commit()
        typer.echo(f"rotated key kid={kid}")
    finally:
        db.close()


if __name__ == "__main__":
    app()
