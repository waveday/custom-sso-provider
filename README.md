# Custom SSO Provider (OIDC)

Google-shape OpenID Connect Provider using your own accounts-style domain.

## Protocol shape / issuer conventions

Set `ISSUER` to your dedicated identity domain:

- Production: `https://accounts.example.com`
- Local dev: `http://accounts.local:8000`

All OIDC URLs are absolute and derived from `ISSUER`:

- Discovery: `{ISSUER}/.well-known/openid-configuration`
- JWKS: `{ISSUER}/jwks.json`
- Authorize: `{ISSUER}/authorize`
- Token: `{ISSUER}/token`
- Userinfo: `{ISSUER}/userinfo`
- Login UI: `{ISSUER}/login`

`iss` in issued ID and access tokens is exactly `ISSUER`.

## Stack

- FastAPI
- Authlib-compatible OIDC server shape (JWT + discovery + JWKS)
- SQLAlchemy + Alembic
- PostgreSQL
- RS256 JWT signing keys with rotation (`kid`, multiple keys, one active)
- Authorization Code flow + PKCE S256 required for all clients

## OIDC behavior

- `response_type=code` only
- `grant_type=authorization_code` only
- scopes: `openid profile email`
- `nonce` is required on `/authorize`
- `state` is returned back unchanged if provided
- exact `redirect_uri` match
- confidential clients: `client_secret_basic` on `/token` + PKCE
- public clients: auth method `none` on `/token` + PKCE

## Local dev

1. Add host mapping:
   - macOS/Linux `/etc/hosts`
   - Windows `C:\Windows\System32\drivers\etc\hosts`

   ```txt
   127.0.0.1 accounts.local
   ```

2. Copy env:

   ```bash
   cp .env.example .env
   ```

   Ensure:

   ```env
   ISSUER=http://accounts.local:8000
   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/oidc
   ```

3. Start dependencies and app:

   ```bash
   docker compose up --build
   ```

4. Direct run option:

   ```bash
   pip install -e .[dev]
   alembic upgrade head
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## Proxy headers

The app enables proxy header handling via `ProxyHeadersMiddleware`.
When deploying behind reverse proxies (Nginx/Caddy/Ingress), pass:

- `X-Forwarded-For`
- `X-Forwarded-Proto`
- `Host`

## Optional local TLS examples

- Caddy example: `deploy/Caddyfile.local`
- Nginx example: `deploy/nginx.local.conf`

Default local mode is HTTP.

## Bootstrap data

Create signing key (required):

```bash
python -m app.cli rotate-key
```

Create a user:

```bash
python -m app.cli create-user \
  --email user@example.com \
  --password pass123 \
  --name "Test User" \
  --given-name Test \
  --family-name User
```

Create confidential client (Laravel-style):

```bash
python -m app.cli create-client \
  --client-name "Laravel App" \
  --redirect-uri http://localhost:9000/callback
```

Create public client (Flutter-style):

```bash
python -m app.cli create-client \
  --client-name "Flutter App" \
  --public \
  --redirect-uri com.example.app:/oauth/callback
```

## Google-like curl examples

### Discovery

```bash
curl -s http://accounts.local:8000/.well-known/openid-configuration | jq
```

### Build authorize URL (PKCE + nonce + state)

```bash
VERIFIER='your_code_verifier_here'
CHALLENGE=$(python - <<'PY'
import base64,hashlib,os
v=os.environ.get('VERIFIER','your_code_verifier_here')
print(base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).decode().rstrip('='))
PY
)

echo "http://accounts.local:8000/authorize?client_id=CLIENT_ID&redirect_uri=http%3A%2F%2Flocalhost%3A9000%2Fcallback&response_type=code&scope=openid%20profile%20email&state=STATE123&nonce=NONCE123&code_challenge=${CHALLENGE}&code_challenge_method=S256"
```

### Token exchange (confidential client + basic auth + PKCE)

```bash
curl -s -X POST http://accounts.local:8000/token \
  -u "CLIENT_ID:CLIENT_SECRET" \
  -d grant_type=authorization_code \
  -d code=AUTH_CODE \
  -d redirect_uri=http://localhost:9000/callback \
  -d code_verifier=YOUR_CODE_VERIFIER
```

### Token exchange (public client + PKCE, no secret)

```bash
curl -s -X POST http://accounts.local:8000/token \
  -d grant_type=authorization_code \
  -d client_id=PUBLIC_CLIENT_ID \
  -d code=AUTH_CODE \
  -d redirect_uri=com.example.app:/oauth/callback \
  -d code_verifier=YOUR_CODE_VERIFIER
```

### Userinfo

```bash
curl -s http://accounts.local:8000/userinfo \
  -H "Authorization: Bearer ACCESS_TOKEN"
```


## VPS deployment (aaPanel)

See detailed guide: [`docs/DEPLOY_AAPANEL.md`](docs/DEPLOY_AAPANEL.md).

## Rate limiting and production hardening

This project includes app-level login/token controls and strong password hashing (`bcrypt`).
For production, put rate limiting at edge (Nginx/Caddy/API Gateway), add IP reputation controls,
account lockout policies, and centralized audit logging.

## Test

```bash
pytest -q
```
