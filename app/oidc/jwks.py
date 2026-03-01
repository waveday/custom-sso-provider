import json

from sqlalchemy.orm import Session

from app.models import SigningKey


def build_jwks(db: Session) -> dict:
    keys = db.query(SigningKey).all()
    return {"keys": [json.loads(k.public_jwk) for k in keys]}
