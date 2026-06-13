"""
setup_decisioning.py  —  SERVER SIDE (one-off)
==============================================
Provisiona o que o serviço `decisioning` (loop fechado) precisa, reusando o
domínio/canal já existentes (lidos de farm_credentials.json):

  1. cria o client `ai-decisioning` conectado ao canal com Publish + Subscribe
     (consome .daily e publica .command);
  2. garante que o client da fazenda (farm-001) também tenha Subscribe
     (para o crop-gym receber .command e fechar o loop);
  3. salva decisioning_credentials.json.

Uso (na EC2, dentro de crop-gym/):
    venv/bin/python scripts/setup_decisioning.py --url http://localhost
"""

import argparse
import json
import sys

import requests

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "12345678"
FARM_CREDS = "farm_credentials.json"
OUT_FILE = "decisioning_credentials.json"


def _raise(r, ctx):
    if not r.ok:
        print(f"[ERROR] {ctx}: HTTP {r.status_code} — {r.text}", file=sys.stderr)
        sys.exit(1)


def get_token(s, base):
    r = s.post(f"{base}/users/tokens/issue",
               json={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    _raise(r, "login")
    return r.json()["access_token"]


def create_client(s, base, token, domain_id, name):
    r = s.post(f"{base}/{domain_id}/clients",
               headers={"Authorization": f"Bearer {token}"},
               json={"name": name})
    _raise(r, "criar client")
    d = r.json()
    return d["id"], d["credentials"]["secret"]


def connect(s, base, token, domain_id, channel_id, client_id, types):
    r = s.post(f"{base}/{domain_id}/channels/{channel_id}/connect",
               headers={"Authorization": f"Bearer {token}"},
               json={"client_ids": [client_id], "types": types})
    # 409/conflict = conexão já existe → ok (idempotente)
    if r.status_code in (409,) or (not r.ok and "already" in r.text.lower()):
        print(f"  conexão {types} já existia para {client_id}")
        return
    _raise(r, f"conectar {types}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost")
    p.add_argument("--creds", default=FARM_CREDS)
    args = p.parse_args()
    base = args.url.rstrip("/")

    with open(args.creds) as f:
        farm = json.load(f)
    domain_id = farm["domain_id"]
    channel_id = farm["channel_id"]
    farm_client_id = farm["client_id"]

    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    token = get_token(s, base)
    print("Autenticado como admin.")

    cid, secret = create_client(s, base, token, domain_id, "ai-decisioning")
    print(f"Client ai-decisioning: {cid}")
    connect(s, base, token, domain_id, channel_id, cid, ["Publish", "Subscribe"])
    print("  conectado ao canal (Publish + Subscribe).")

    # farm-001 precisa de Subscribe para receber os comandos (.command)
    connect(s, base, token, domain_id, channel_id, farm_client_id, ["Subscribe"])
    print("  farm-001: Subscribe garantido.")

    out = {
        "domain_id": domain_id,
        "channel_id": channel_id,
        "client_id": cid,
        "client_secret": secret,
    }
    with open(OUT_FILE, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nCredenciais salvas em '{OUT_FILE}':")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
