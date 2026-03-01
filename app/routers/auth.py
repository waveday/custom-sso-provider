from urllib.parse import urlencode
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AuthCode, OAuthClient, User
from app.security import expiry_from_now, make_auth_code, now_utc, verify_password

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _validate_authz_params(
    db: Session,
    client_id: str,
    redirect_uri: str,
    response_type: str,
    scope: str,
    code_challenge: str,
    code_challenge_method: str,
    nonce: str,
) -> OAuthClient:
    if response_type != "code":
        raise HTTPException(status_code=400, detail={"error": "unsupported_response_type"})
    if not nonce:
        raise HTTPException(status_code=400, detail={"error": "invalid_request", "error_description": "nonce is required"})
    if code_challenge_method != "S256" or not code_challenge:
        raise HTTPException(status_code=400, detail={"error": "invalid_request", "error_description": "PKCE S256 required"})
    scopes = set(scope.split())
    if "openid" not in scopes:
        raise HTTPException(status_code=400, detail={"error": "invalid_scope"})
    client = db.query(OAuthClient).filter_by(client_id=client_id).first()
    if not client:
        raise HTTPException(status_code=400, detail={"error": "unauthorized_client"})
    if redirect_uri not in [u.strip() for u in client.redirect_uris.split() if u.strip()]:
        raise HTTPException(status_code=400, detail={"error": "invalid_request", "error_description": "redirect_uri mismatch"})
    return client


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/authorize")
def authorize(
    request: Request,
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query(...),
    scope: str = Query("openid profile email"),
    state: Optional[str] = Query(None),
    nonce: str = Query(...),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query(...),
    db: Session = Depends(get_db),
):
    _validate_authz_params(db, client_id, redirect_uri, response_type, scope, code_challenge, code_challenge_method, nonce)
    request.session["auth_request"] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }
    if request.session.get("user_id"):
        return RedirectResponse(url="/consent", status_code=302)
    return RedirectResponse(url="/login", status_code=302)


@router.get("/consent", response_class=HTMLResponse)
def consent_page(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login", status_code=302)
    auth_request = request.session.get("auth_request")
    if not auth_request:
        raise HTTPException(status_code=400, detail="Missing authorization request")
    client = db.query(OAuthClient).filter_by(client_id=auth_request["client_id"]).first()
    if not client:
        raise HTTPException(status_code=400, detail="Invalid client")
    return templates.TemplateResponse(
        "consent.html", {"request": request, "client_name": client.client_name, "scope": auth_request["scope"]}
    )


@router.post("/login")
def login_submit(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=email).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    request.session["user_id"] = user.id
    return RedirectResponse(url="/consent", status_code=302)


@router.post("/authorize/approve")
def approve_authorize(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    auth_request = request.session.get("auth_request")
    if not user_id or not auth_request:
        raise HTTPException(status_code=400, detail="Missing auth context")
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid user")

    code = make_auth_code()
    auth_code = AuthCode(
        code=code,
        client_id=auth_request["client_id"],
        user_id=user.id,
        redirect_uri=auth_request["redirect_uri"],
        scope=auth_request["scope"],
        state=auth_request.get("state"),
        nonce=auth_request["nonce"],
        code_challenge=auth_request["code_challenge"],
        code_challenge_method=auth_request["code_challenge_method"],
        expires_at=expiry_from_now(get_settings().auth_code_ttl_seconds),
    )
    db.add(auth_code)
    db.commit()

    params = {"code": code}
    if auth_request.get("state"):
        params["state"] = auth_request["state"]
    request.session.pop("auth_request", None)
    return RedirectResponse(url=f"{auth_request['redirect_uri']}?{urlencode(params)}", status_code=302)


@router.post("/authorize/deny")
def deny_authorize(request: Request):
    auth_request = request.session.get("auth_request")
    if not auth_request:
        raise HTTPException(status_code=400, detail="Missing auth context")
    params = {"error": "access_denied"}
    if auth_request.get("state"):
        params["state"] = auth_request["state"]
    request.session.pop("auth_request", None)
    return RedirectResponse(url=f"{auth_request['redirect_uri']}?{urlencode(params)}", status_code=302)
