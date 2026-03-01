from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.oidc.discovery import discovery_document
from app.oidc.jwks import build_jwks

router = APIRouter()


@router.get("/.well-known/openid-configuration")
def openid_configuration():
    return discovery_document()


@router.get("/jwks.json")
def jwks(db: Session = Depends(get_db)):
    return build_jwks(db)
