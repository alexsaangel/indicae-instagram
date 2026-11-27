"""Busca uma notícia de Sobral, monta legenda + artes e salva em posts/<data>/.

Saída: imprime o caminho da pasta do post (ou nada, se não achou notícia boa).
O workflow do GitHub usa essa pasta para abrir a Issue de prévia.
"""
import html
import json
import os
import random
import re
import sys
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import feedparser

sys.path.insert(0, str(Path(__file__).resolve().parent))
import arte  # noqa: E402
import reel  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
HISTORICO = RAIZ / "dados" / "historico.json"
FUSO = timezone(timedelta(hours=-3))
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def carregar_historico():
    if HISTORICO.exists():
        return json.loads(HISTORICO.read_text(encoding="utf-8"))
    return {"links": [], "titulos": []}


def limpar(texto):
    texto = html.unescape(re.sub(r"<[^>]+>", " ", texto or ""))
    return re.sub(r"\s+", " ", texto).strip()


def separar_fonte(titulo):
    # Google Notícias: "Título da matéria - Nome do Veículo"
    if " - " in titulo:
        t, f = titulo.rsplit(" - ", 1)
        return t.strip(), f.strip()
    return titulo.strip(), "imprensa local"


def proibida(texto):
    t = texto.lower()
    # compara pelo começo da palavra ("presa" não pega "empresa")
    return any(re.search(r"(?<!\w)" + re.escape(p.strip()), t) for p in CONFIG["palavras_proibidas"])


def buscar_noticias(feeds=None):
    if feeds is None:
        feeds = [
            "https://news.google.com/rss/search?q=" + urllib.parse.quote(q + " when:30d")
            + "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
            for q in CONFIG["buscas_noticias"]
        ]
    itens = []
    for url in feeds:
        for e in feedparser.parse(url).entries:
            titulo, fonte = separar_fonte(limpar(e.get("title")))
            itens.append({"titulo": titulo, "fonte": "Fonte: " + fonte, "link": e.get("link", ""),
                          "resumo": limpar(e.get("summary"))})
    return itens


def escolher(itens, hist):
    vistos = set(hist["links"]) | {t.lower() for t in hist["titulos"]}
    for it in itens:
        if it["link"] in vistos or it["titulo"].lower() in vistos:
            continue
        texto = (it["titulo"] + " " + it["resumo"]).lower()
        if not any(p.lower() in texto for p in CONFIG["palavras_relevantes"]):
            continue
        if proibida(it["titulo"] + " " + it["resumo"]):
            continue
        if len(it["titulo"]) < 25:
            continue
        return it
    return None


def montar_legenda(it):
    chamada = random.choice(CONFIG["chamadas"])
    return (
        f"💡 {it['titulo']}\n\n"
        f"{it['fonte']}. A matéria completa está no site do veículo.\n\n"
        f"{chamada}\n"
        f"👉 {CONFIG['site']}\n\n"
        f"{CONFIG['hashtags']}"
    )


def conteudo_proprio(hist):
    """Dias sem notícia boa: usa o rodízio de conteúdos do Indicaê."""
    lista = CONFIG["conteudos_proprios"]
    i = hist.get("rodizio", 0) % len(lista)
    hist["rodizio"] = i + 1
    c = lista[i]
    legenda = f"{c['texto']}\n\n{CONFIG['chamada_final']}\n\n{CONFIG['hashtags']}"
    return {"titulo": c["titulo"], "fonte": CONFIG["site"], "link": f"proprio-{i}",
            "resumo": "", "selo": c["selo"], "legenda": legenda, "apoio": c.get("apoio"),
            "slides": c.get("slides")}


def main(feeds=None, forcar_proprio=False):
    hist = carregar_historico()
    it = None if forcar_proprio else escolher(buscar_noticias(feeds), hist)
    if not it:
        it = conteudo_proprio(hist)

    agora = datetime.now(FUSO)
    pasta = RAIZ / "posts" / agora.strftime("%Y-%m-%d")
    data_txt = f"{agora.day} de {MESES[agora.month - 1]} de {agora.year}"
    arte.gerar(it["titulo"], it["fonte"], data_txt, CONFIG["cores"], CONFIG["site"], it.get("selo", CONFIG["selo"]),
               pasta / "feed.jpg", pasta / "stories.jpg")

    hist["total"] = hist.get("total", 0) + 1
    if it.get("slides"):
        arquivos = arte.gerar_carrossel(it["titulo"], it["slides"], CONFIG["cores"], CONFIG["site"],
                                        it.get("selo", CONFIG["selo"]), pasta)
        it["carrossel"] = [a.name for a in arquivos]
    elif hist["total"] % CONFIG.get("reel_a_cada", 2) == 0:
        try:
            reel.gerar(it["titulo"], it.get("apoio") or CONFIG["apoio_padrao"], CONFIG["cores"],
                       CONFIG["site"], it.get("selo", CONFIG["selo"]), pasta / "reel.mp4")
        except Exception as e:  # sem vídeo, segue como foto
            print(f"Reel não gerado: {e}", file=sys.stderr)

    post = {**it, "legenda": it.get("legenda") or montar_legenda(it), "criado_em": agora.isoformat()}
    (pasta / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")

    if not it["link"].startswith("proprio-"):
        hist["links"].append(it["link"])
        hist["titulos"].append(it["titulo"])
    hist["links"], hist["titulos"] = hist["links"][-300:], hist["titulos"][-300:]
    HISTORICO.parent.mkdir(exist_ok=True)
    HISTORICO.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")

    print(pasta.relative_to(RAIZ).as_posix())
    return pasta


if __name__ == "__main__":
    main(forcar_proprio=os.environ.get("CONTEUDO_PROPRIO") == "1")
