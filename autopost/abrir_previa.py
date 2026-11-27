"""Abre a Issue de prévia no GitHub (você recebe aviso por e-mail e no app)."""
import json
import os
import sys
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
REPO = os.environ["GITHUB_REPOSITORY"]
RAMO = os.environ.get("GITHUB_REF_NAME", "main")
H = {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json"}


def garantir_etiquetas():
    cores = {"aguardando": "F2622E", "cancelar": "B60205", "publicado": "0E8A16", "erro": "FBCA04"}
    for nome, cor in cores.items():
        requests.post(f"https://api.github.com/repos/{REPO}/labels", headers=H,
                      json={"name": nome, "color": cor}, timeout=30)  # ignora se já existe


def main(pasta):
    post = json.loads((RAIZ / pasta / "post.json").read_text(encoding="utf-8"))
    base = f"https://raw.githubusercontent.com/{REPO}/{RAMO}/{pasta}"
    horas = CONFIG["horas_para_cancelar"]
    corpo = f"""## Prévia do próximo post

Vai ser publicado sozinho em **{horas} horas**, a menos que você cancele.

**Para cancelar:** feche esta Issue, ou adicione a etiqueta `cancelar`.
**Para mudar a legenda:** edite esta descrição (só o texto dentro do bloco da legenda).

### Feed
{"".join(f'<img src="{base}/{f}" width="180"> ' for f in post.get("carrossel", [])) or f'<img src="{base}/feed.jpg" width="360">'}

{"### Reel (vídeo)" + chr(10) + f"[▶️ Assistir o Reel]({base}/reel.mp4) — este post sai como Reel." + chr(10) if (RAIZ / pasta / "reel.mp4").exists() else ""}
### Stories
<img src="{base}/stories.jpg" width="240">

### Legenda
<!--legenda-->
```text
{post['legenda']}
```

Notícia original: {post['link']}

<!--pasta-->
```text
{pasta}
```
"""
    garantir_etiquetas()
    r = requests.post(f"https://api.github.com/repos/{REPO}/issues", headers=H, timeout=30,
                      json={"title": f"📸 Prévia: {post['titulo'][:80]}", "body": corpo,
                            "labels": ["aguardando"]})
    r.raise_for_status()
    print(r.json()["html_url"])


if __name__ == "__main__":
    main(sys.argv[1])
