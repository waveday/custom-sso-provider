from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.routers.auth import router as auth_router
from app.routers.oidc import router as oidc_router
from app.routers.token import router as token_router

settings = get_settings()
app = FastAPI(title="Custom OIDC Provider")
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.app_secret,
    https_only=settings.secure_cookies or str(settings.issuer).startswith("https://"),
    same_site="lax",
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

app.include_router(oidc_router)
app.include_router(auth_router)
app.include_router(token_router)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}
