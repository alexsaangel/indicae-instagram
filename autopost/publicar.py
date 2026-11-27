"""Publica no Instagram os posts aprovados.

Olha as Issues abertas com a etiqueta "aguardando". Se já passou o prazo de
cancelamento e a Issue NÃO tem a etiqueta "cancelar", publica feed + stories
usando a legenda que estiver na Issue (então dá para editar a legenda lá).
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
IG_API = "https://graph.facebook.com/v21.0"
GH_API = "https://api.github.com"

REPO = os.environ.get("GITHUB_REPOSITORY", "")
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")
IG_TOKEN = os.environ.get("IG_TOKEN", "")
IG_USER_ID = os.environ.get("IG_USER_ID", "")
MAKE_WEBHOOK = os.environ.get("MAKE_WEBHOOK", "")


def gh(metodo, caminho, **kw):
    r = requests.request(metodo, f"{GH_API}/repos/{REPO}{caminho}",
                         headers={"Authorization": f"Bearer {GH_TOKEN}",
                                  "Accept": "application/vnd.github+json"}, timeout=30, **kw)
    r.raise_for_status()
    return r.json() if r.text else {}


def extrair(corpo, marcador):
    m = re.search(rf"<!--{marcador}-->\s*```(?:text)?\n(.*?)\n```", corpo, re.S)
    return m.group(1).strip() if m else None


def ig_criar(params):
    params = {**params, "access_token": IG_TOKEN}
    r = requests.post(f"{IG_API}/{IG_USER_ID}/media", data=params, timeout=60)
    if not r.ok:
        raise RuntimeError(f"Instagram recusou a mídia: {r.text}")
    cid = r.json()["id"]
    for _ in range(30):  # espera o Instagram processar a imagem
        s = requests.get(f"{IG_API}/{cid}", params={"fields": "status_code",
                                                    "access_token": IG_TOKEN}, timeout=30).json()
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram não processou a imagem: {s}")
        time.sleep(5)
    r = requests.post(f"{IG_API}/{IG_USER_ID}/media_publish",
                      data={"creation_id": cid, "access_token": IG_TOKEN}, timeout=60)
    if not r.ok:
        raise RuntimeError(f"Instagram recusou a publicação: {r.text}")
    return r.json()["id"]


def carrossel(pasta):
    try:
        post = json.loads((RAIZ / pasta / "post.json").read_text(encoding="utf-8"))
        return post.get("carrossel") or []
    except Exception:
        return []


def via_make(pasta, legenda):
    """Envia o post ao Make.com, que publica com o app aprovado pela Meta."""
    r = requests.post(MAKE_WEBHOOK, json={
        "feed_url": url_publica(pasta, "feed.jpg"),
        "stories_url": url_publica(pasta, "stories.jpg"),
        "video_url": url_publica(pasta, "reel.mp4") if (RAIZ / pasta / "reel.mp4").exists() else "",
        "legenda": legenda,
        "carrossel_urls": [url_publica(pasta, f) for f in carrossel(pasta)],
    }, timeout=120)
    if not r.ok:
        raise RuntimeError(f"Make recusou: {r.status_code} {r.text[:300]}")
    return r.text.strip()[:200] or "enviado ao Make"


def url_publica(pasta, arquivo):
    ramo = os.environ.get("GITHUB_REF_NAME", "main")
    return f"https://raw.githubusercontent.com/{REPO}/{ramo}/{pasta}/{arquivo}"


def main():
    if not (GH_TOKEN and REPO and (MAKE_WEBHOOK or (IG_TOKEN and IG_USER_ID))):
        sys.exit("Falta o segredo MAKE_WEBHOOK (ou IG_TOKEN + IG_USER_ID) no GitHub.")

    prazo = timedelta(hours=CONFIG["horas_para_cancelar"])
    agora = datetime.now(timezone.utc)
    issues = gh("GET", "/issues", params={"state": "open", "labels": "aguardando"})

    for issue in issues:
        etiquetas = {l["name"] for l in issue["labels"]}
        n = issue["number"]
        criada = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
        if "cancelar" in etiquetas:
            gh("POST", f"/issues/{n}/comments", json={"body": "🚫 Cancelado. Não vou publicar este."})
            gh("PATCH", f"/issues/{n}", json={"state": "closed", "state_reason": "not_planned"})
            continue
        if agora - criada < prazo and os.environ.get("PUBLICAR_AGORA") != "true":
            print(f"#{n}: ainda dentro do prazo de cancelamento.")
            continue

        corpo = issue.get("body") or ""
        pasta = extrair(corpo, "pasta")
        legenda = extrair(corpo, "legenda")
        if not pasta or not legenda:
            gh("POST", f"/issues/{n}/comments", json={"body": "⚠️ Não encontrei a legenda ou a pasta na descrição. Não publiquei."})
            continue

        try:
            if MAKE_WEBHOOK:
                feed_id = via_make(pasta, legenda)
                story_id = "(pelo Make)"
            else:
                feed_id = ig_criar({"image_url": url_publica(pasta, "feed.jpg"), "caption": legenda})
                story_id = ig_criar({"image_url": url_publica(pasta, "stories.jpg"), "media_type": "STORIES"})
        except Exception as e:  # avisa na própria Issue e segue
            gh("POST", f"/issues/{n}/comments", json={"body": f"❌ Erro ao publicar:\n\n```\n{e}\n```"})
            gh("POST", f"/issues/{n}/labels", json={"labels": ["erro"]})
            continue

        gh("POST", f"/issues/{n}/comments",
           json={"body": f"✅ Publicado no Instagram!\n\nFeed: `{feed_id}` · Stories: `{story_id}`"})
        gh("POST", f"/issues/{n}/labels", json={"labels": ["publicado"]})
        gh("DELETE", f"/issues/{n}/labels/aguardando")
        gh("PATCH", f"/issues/{n}", json={"state": "closed"})


if __name__ == "__main__":
    main()
