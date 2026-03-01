# Deploy on aaPanel (VPS)

This guide shows how to run this OIDC Provider on a VPS managed by **aaPanel** with an `accounts` style issuer domain.

Example production issuer:

```env
ISSUER=https://accounts.example.com
```

---

## 1) Prerequisites

- A VPS with aaPanel installed
- A DNS record:
  - `accounts.example.com -> <your_vps_public_ip>`
- aaPanel plugins:
  - **Nginx Manager**
  - **Supervisor Manager** (or PM2/Supervisor equivalent)
  - **Python Project Manager** (optional)
  - **Docker Manager** (optional if you use Compose)

---

## 2) Upload project and prepare runtime

SSH to VPS (or use aaPanel File Manager terminal):

```bash
cd /www/wwwroot
git clone <your-repo-url> custom-sso-provider
cd custom-sso-provider
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

Create env file:

```bash
cp .env.example .env
```

Set production values in `.env`:

```env
ISSUER=https://accounts.example.com
DATABASE_URL=postgresql+psycopg://oidc_user:strong_password@127.0.0.1:5432/oidc
APP_SECRET=<long-random-secret>
ACCESS_TOKEN_TTL_SECONDS=3600
ID_TOKEN_TTL_SECONDS=3600
AUTH_CODE_TTL_SECONDS=300
SECURE_COOKIES=true
```

> `ISSUER` must exactly match your public URL. It is used in discovery docs and `iss` claim validation.

---

## 3) Database and migration

Create Postgres DB/user (via aaPanel PostgreSQL plugin or CLI), then run:

```bash
cd /www/wwwroot/custom-sso-provider
source .venv/bin/activate
alembic upgrade head
```

Bootstrap at least one signing key and one admin/test user:

```bash
python -m app.cli rotate-key
python -m app.cli create-user \
  --email admin@example.com \
  --password 'ChangeMeNow!' \
  --name 'Admin User' \
  --given-name Admin \
  --family-name User
```

---

## 4) Run app with Supervisor (recommended in aaPanel)

In **aaPanel > Supervisor Manager > Add Daemon**:

- **Name**: `custom-sso-provider`
- **Run Directory**: `/www/wwwroot/custom-sso-provider`
- **Start Command**:

```bash
bash -lc 'source /www/wwwroot/custom-sso-provider/.venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000'
```

- **Auto Start**: enabled

Start service and confirm:

```bash
curl -s http://127.0.0.1:8000/healthz
```

---

## 5) Configure aaPanel Nginx reverse proxy

Create website in aaPanel:

- **Domain**: `accounts.example.com`
- **Root**: any folder (app is reverse proxied, static root is not used)

In site Nginx config, proxy to local uvicorn:

```nginx
server {
    listen 80;
    listen 443 ssl http2;
    server_name accounts.example.com;

    # TLS managed by aaPanel SSL UI
    # ssl_certificate ...
    # ssl_certificate_key ...

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

The app already trusts proxy headers (`ProxyHeadersMiddleware`), so the forwarded proto/host are important for correct URL behavior.

---

## 6) Enable HTTPS (required for production)

In aaPanel site SSL settings:

- Use Let's Encrypt certificate for `accounts.example.com`
- Force HTTPS redirect

Because `ISSUER` is `https://...`, secure cookie behavior is applied.

---

## 7) Verify OIDC endpoints

```bash
curl -s https://accounts.example.com/.well-known/openid-configuration | jq .issuer
curl -s https://accounts.example.com/jwks.json | jq .
```

Expected issuer output:

```txt
"https://accounts.example.com"
```

---

## 8) Firewall checklist

- Open inbound: `80`, `443`
- Keep `8000` private (localhost only through Nginx)
- Restrict PostgreSQL access to local/private network

---

## 9) Optional: Docker Compose on aaPanel

If you prefer containers:

```bash
cd /www/wwwroot/custom-sso-provider
docker compose up -d --build
```

Then configure aaPanel Nginx proxy to `127.0.0.1:8000` the same way as above.

---

## 10) Upgrade workflow

```bash
cd /www/wwwroot/custom-sso-provider
git pull
source .venv/bin/activate
pip install -e .
alembic upgrade head
supervisorctl restart custom-sso-provider
```

In aaPanel UI, this restart is available in Supervisor Manager.
