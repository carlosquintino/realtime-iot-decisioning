"""
magistrala_setup.py  —  SERVER SIDE
====================================
Run this ONCE on the machine that hosts Magistrala to provision one farm.
It creates a domain, a client (the farm) and a channel (crop data stream),
connects them, then writes farm_credentials.json.

That JSON file is the only thing the farm computer needs; it has no access
to Magistrala internals.

Usage:
    python magistrala_setup.py
    python magistrala_setup.py --url http://192.168.1.100 --farm-id farm-001
"""

import argparse
import json
import sys
import requests

# ── defaults (match supermq-docker/.env) ────────────────────────────────────
DEFAULT_URL      = "http://localhost"
ADMIN_EMAIL      = "admin@example.com"
ADMIN_PASSWORD   = "12345678"
DOMAIN_NAME      = "crop-farms"
CHANNEL_NAME     = "crop-data"
CREDENTIALS_FILE = "farm_credentials.json"
# ─────────────────────────────────────────────────────────────────────────────


def _raise(r: requests.Response, context: str):
    if not r.ok:
        print(f"[ERROR] {context}: HTTP {r.status_code} — {r.text}", file=sys.stderr)
        sys.exit(1)


def get_token(session: requests.Session, base: str) -> str:
    r = session.post(f"{base}/users/tokens/issue", json={
        "username": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    _raise(r, "login")
    token = r.json()["access_token"]
    print("  Autenticado como admin.")
    return token


def create_domain(session: requests.Session, base: str, token: str) -> str:
    r = session.post(f"{base}/domains",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": DOMAIN_NAME, "alias": DOMAIN_NAME},
    )
    # 409 = já existe; busca pelo alias
    if r.status_code == 409:
        print(f"  Domain '{DOMAIN_NAME}' já existe, buscando ID...")
        r2 = session.get(f"{base}/domains",
            headers={"Authorization": f"Bearer {token}"},
            params={"name": DOMAIN_NAME},
        )
        _raise(r2, "buscar domain")
        domains = r2.json().get("domains", [])
        match = next((d for d in domains if d["alias"] == DOMAIN_NAME), None)
        if not match:
            print("[ERROR] Domain não encontrado após conflito.", file=sys.stderr)
            sys.exit(1)
        return match["id"]
    _raise(r, "criar domain")
    return r.json()["id"]


def create_client(session: requests.Session, base: str, token: str,
                  domain_id: str, farm_id: str) -> tuple[str, str]:
    r = session.post(f"{base}/{domain_id}/clients",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": farm_id},
    )
    _raise(r, "criar client")
    data = r.json()
    return data["id"], data["credentials"]["secret"]


def create_channel(session: requests.Session, base: str, token: str,
                   domain_id: str) -> str:
    r = session.post(f"{base}/{domain_id}/channels",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": CHANNEL_NAME},
    )
    _raise(r, "criar channel")
    return r.json()["id"]


def connect_client(session: requests.Session, base: str, token: str,
                   domain_id: str, channel_id: str, client_id: str):
    r = session.post(f"{base}/{domain_id}/channels/{channel_id}/connect",
        headers={"Authorization": f"Bearer {token}"},
        json={"client_ids": [client_id], "types": ["Publish"]},
    )
    _raise(r, "conectar client ao channel")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url",     default=DEFAULT_URL, help="URL base do Magistrala")
    parser.add_argument("--farm-id", default="farm-001",  help="Nome/ID da fazenda")
    args = parser.parse_args()

    base    = args.url.rstrip("/")
    farm_id = args.farm_id

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    print(f"Provisionando '{farm_id}' em {base}...")

    token      = get_token(session, base)
    domain_id  = create_domain(session, base, token)
    print(f"  Domain:  {domain_id}")

    client_id, client_secret = create_client(session, base, token, domain_id, farm_id)
    print(f"  Client:  {client_id}")

    channel_id = create_channel(session, base, token, domain_id)
    print(f"  Channel: {channel_id}")

    connect_client(session, base, token, domain_id, channel_id, client_id)
    print("  Client conectado ao channel (Publish).")

    # HTTP adapter URL — o único endpoint que a fazenda precisa conhecer
    http_adapter_url = f"{base}/http"

    credentials = {
        "farm_id":          farm_id,
        "magistrala_url":   base,
        "http_adapter_url": http_adapter_url,
        "channel_id":       channel_id,
        "client_id":        client_id,
        "client_secret":    client_secret,
    }

    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(credentials, f, indent=2)

    print(f"\nCredenciais salvas em '{CREDENTIALS_FILE}'.")
    print("Entregue esse arquivo ao operador da fazenda.")
    print(json.dumps(credentials, indent=2))


if __name__ == "__main__":
    main()
