"""FreeDomain reference application.

The application intentionally keeps registrar-specific behavior behind a small
adapter. Set REGISTRAR_MODE=provider and configure the provider URL/token only
when the provider's API contract has been verified.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).parent
DATABASE = Path(os.getenv("DATABASE_PATH", ROOT / "data" / "freedomain.db"))
TLD_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
SUPPORTED_TLDS = (".dpdns.org", ".us.kg", ".qzz.io", ".xx.kg", ".qd.je")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db() -> sqlite3.Connection:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS registrations (
            id TEXT PRIMARY KEY, domain TEXT NOT NULL UNIQUE, email TEXT NOT NULL,
            nameservers TEXT NOT NULL, status TEXT NOT NULL, provider_id TEXT,
            created_at TEXT NOT NULL
        )"""
    )
    return connection


def validate_domain(domain: str) -> str:
    normalized = domain.strip().lower().rstrip(".")
    suffix = next((tld for tld in SUPPORTED_TLDS if normalized.endswith(tld)), None)
    if not suffix:
        raise ValueError("Use one of the supported free extensions.")
    label = normalized[: -len(suffix)]
    if not TLD_PATTERN.fullmatch(label):
        raise ValueError("The domain name may contain lowercase letters, numbers, and hyphens.")
    return normalized


def redact_email(email: str) -> str:
    local, separator, host = email.partition("@")
    if not separator or not local or not host:
        return "***"
    return f"{local[:1]}***@{host}"


def provider_register(domain: str, email: str, nameservers: list[str]) -> dict[str, Any]:
    mode = os.getenv("REGISTRAR_MODE", "demo").lower()
    if mode == "demo":
        return {"status": "pending", "provider_id": f"demo-{secrets.token_hex(6)}"}
    if mode != "provider":
        raise RuntimeError("REGISTRAR_MODE must be demo or provider.")

    url = os.getenv("REGISTRAR_REGISTER_URL")
    token = os.getenv("REGISTRAR_API_TOKEN")
    if not url or not token:
        raise RuntimeError("REGISTRAR_REGISTER_URL and REGISTRAR_API_TOKEN are required.")
    response = requests.post(
        url,
        json={"domain": domain, "email": email, "nameservers": nameservers},
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    return {
        "status": str(payload.get("status", "pending")),
        "provider_id": str(payload.get("id", payload.get("provider_id", ""))),
    }


def create_app() -> Flask:
    app = Flask(__name__, static_folder="web", static_url_path="/web")
    app.config["JSON_SORT_KEYS"] = False

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'"
        )
        return response

    @app.get("/")
    def index():
        return send_from_directory(ROOT / "web", "index.html")

    @app.get("/health")
    def health():
        return jsonify({"status": "healthy", "service": "freedomain", "registrar_mode": os.getenv("REGISTRAR_MODE", "demo")})

    @app.get("/api/extensions")
    def extensions():
        return jsonify({"extensions": list(SUPPORTED_TLDS)})

    @app.get("/api/registrations")
    def registrations():
        # A deployment should put this endpoint behind account authentication.
        rows = db().execute(
            "SELECT id, domain, email, nameservers, status, created_at FROM registrations ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
        return jsonify({"registrations": [dict(row) | {"email": redact_email(row["email"])} for row in rows]})

    @app.post("/api/registrations")
    def register():
        body = request.get_json(silent=True) or {}
        domain = body.get("domain", "")
        email = body.get("email", "").strip().lower()
        nameservers = body.get("nameservers", [])
        if not isinstance(nameservers, list) or not all(isinstance(value, str) for value in nameservers):
            return jsonify({"error": "nameservers must be a list of hostnames"}), 400
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            return jsonify({"error": "A valid email address is required."}), 400
        try:
            domain = validate_domain(domain)
            if len(nameservers) < 2 or len(nameservers) > 4:
                raise ValueError("Provide between two and four authoritative nameservers.")
            result = provider_register(domain, email, nameservers)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        except (requests.RequestException, RuntimeError) as error:
            return jsonify({"error": str(error)}), 502

        registration_id = secrets.token_urlsafe(12)
        with db() as connection:
            try:
                connection.execute(
                    "INSERT INTO registrations VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (registration_id, domain, email, ",".join(nameservers), result["status"], result["provider_id"], utc_now()),
                )
            except sqlite3.IntegrityError:
                return jsonify({"error": "That domain already has a registration request."}), 409
        return jsonify({"id": registration_id, "domain": domain, **result}), 201

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "5000")))
