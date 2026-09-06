# FreeDomain deployment

This repository now includes a small registration portal in `app.py`, a
responsive browser UI in `web/`, and a SQLite persistence layer. It is a
reference implementation for the DigitalPlat workflow described in the
learning guide, not a replacement for the official DigitalPlat dashboard.

## Local run

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. The default `REGISTRAR_MODE=demo` stores requests
locally and never registers a real domain.

## Provider mode

Set `REGISTRAR_MODE=provider`, `REGISTRAR_REGISTER_URL`, and
`REGISTRAR_API_TOKEN` only after confirming the provider's current API contract.
Tokens must remain in an environment or secret manager. The adapter sends
`domain`, `email`, and `nameservers` as JSON and expects `status` and `id` (or
`provider_id`) in the response.

## Production checklist

- Put the API behind TLS and an identity layer before exposing account data.
- Replace the demo SQLite database with PostgreSQL for multiple instances.
- Add provider webhooks and an authenticated account/session system.
- Configure backups using `scripts/backup.ps1` and monitor `/health`.
- Follow the existing [security guide](../documents/tutorial/operations/5.5-security.md)
  and [DigitalPlat API guide](../documents/tutorial/platform/1.6-api-overview.md).

The original enterprise snippets in the supplied material are useful as
architecture ideas, but hard-coded passwords, fallback secrets, and unverified
provider calls were intentionally not copied into the application.
