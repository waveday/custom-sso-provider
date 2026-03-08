# Quick Start

## Create mobile app 

```bash
cd /www/wwwroot/Muath/custom-sso-provider
```

```bash
source .venv/bin/activate
```

```bash
python -m app.cli create-client "Flutter Aytamna App" --redirect-uri "http://localhost:9000/callback"
```

## Create a user

```bash
python -m app.cli create-user "amjad@muathye.com" "123456789" "Amjad User" "Test" "Family"
```

email="amjad@muathye.com"
password="123456789"
name="Amjad User"
given-name="Test"
family-name="Family"