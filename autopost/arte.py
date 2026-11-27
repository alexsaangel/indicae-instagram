"""Gera as artes do feed (1080x1350) e do stories (1080x1920) no visual do Indicaê."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / "fonts"


def _fonte(nome, tamanho):
    return ImageFont.truetype(str(FONTES / nome), tamanho)


def _quebrar(draw, texto, fonte, largura_max):
    palavras, linhas, atual = texto.split(), [], ""
    for p in palavras:
        teste = f"{atual} {p}".strip()
        if draw.textlength(teste, font=fonte) <= largura_max:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def _titulo_que_cabe(draw, texto, largura, altura_max, tamanhos):
    """Diminui a fonte até o título caber no espaço."""
    for t in tamanhos:
        f = _fonte("Fraunces-800.woff", t)
        linhas = _quebrar(draw, texto, f, largura)
        alt = len(linhas) * int(t * 1.15)
        maior = max(draw.textlength(l, font=f) for l in linhas)
        if alt <= altura_max and maior <= largura:
            return f, linhas, int(t * 1.15)
    # último recurso: corta com reticências
    f = _fonte("Fraunces-800.woff", tamanhos[-1])
    lh = int(tamanhos[-1] * 1.15)
    linhas = _quebrar(draw, texto, f, largura)[: max(1, altura_max // lh)]
    linhas[-1] = linhas[-1].rstrip(".,;:") + "…"
    return f, linhas, lh


def _pilula(draw, x, y, texto, fonte, fundo, cor):
    w = draw.textlength(texto, font=fonte)
    pad_x, alt = 28, fonte.size + 26
    draw.rounded_rectangle([x, y, x + w + pad_x * 2, y + alt], radius=alt // 2, fill=fundo)
    draw.text((x + pad_x, y + alt / 2), texto, font=fonte, fill=cor, anchor="lm")
    return alt


def gerar(titulo, fonte_noticia, data_txt, cores, site, selo, destino_feed, destino_story):
    _desenhar(1080, 1350, titulo, fonte_noticia, data_txt, cores, site, selo, destino_feed, story=False)
    _desenhar(1080, 1920, titulo, fonte_noticia, data_txt, cores, site, selo, destino_story, story=True)


def _desenhar(W, H, titulo, fonte_noticia, data_txt, cores, site, selo, destino, story):
    img = Image.new("RGB", (W, H), cores["fundo"])
    d = ImageDraw.Draw(img)
    m = 90
    topo = 200 if story else 110

    # detalhe decorativo: círculo laranja no canto
    r = 260
    d.ellipse([W - r, -r, W + r, r], fill=cores["laranja"])

    # selo
    _pilula(d, m, topo, selo, _fonte("inter-latin-700-normal.woff", 30), cores["petroleo"], cores["fundo"])
    d.text((m, topo + 110), data_txt, font=_fonte("inter-latin-600-normal.woff", 32), fill=cores["texto_suave"])

    # faixa inferior
    faixa = 230 if story else 190
    d.rectangle([0, H - faixa, W, H], fill=cores["petroleo"])
    d.text((m, H - faixa + 55), "Indicaê", font=_fonte("Fraunces-800.woff", 58), fill=cores["fundo"])
    d.text((m, H - faixa + 130), f"A confiança circula · {site}", font=_fonte("inter-latin-400-normal.woff", 30), fill=cores["fundo"])

    # título
    ini = topo + 200
    fim = H - faixa - (260 if story else 170)
    tamanhos = [96, 88, 80, 72, 66, 60, 54] if story else [88, 80, 72, 66, 60, 54, 48]
    f, linhas, lh = _titulo_que_cabe(d, titulo, W - 2 * m - 40, fim - ini, tamanhos)
    bloco = len(linhas) * lh
    y = ini + max(0, (fim - ini - bloco) // 3)
    d.rectangle([m, y + 8, m + 10, y + bloco - 8], fill=cores["laranja"])
    for ln in linhas:
        d.text((m + 40, y), ln, font=f, fill=cores["petroleo"])
        y += lh

    d.text((m + 40, y + 30), f"{fonte_noticia}", font=_fonte("inter-latin-600-normal.woff", 32), fill=cores["texto_suave"])

    if story:
        _pilula(d, m, H - faixa - 170, "Conheça o Indicaê: link na bio", _fonte("inter-latin-700-normal.woff", 34), cores["laranja"], "#FFFFFF")

    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "JPEG", quality=92)


def gerar_carrossel(titulo, slides, cores, site, selo, pasta):
    """Capa + 1 slide por item + slide final. Retorna a lista de arquivos (máx. 10)."""
    W, H = 1080, 1350
    arquivos = []
    # capa
    capa = pasta / "carrossel_01.jpg"
    pasta.mkdir(parents=True, exist_ok=True)
    _desenhar(W, H, titulo, "Arrasta pro lado e salva", "", cores, site, selo, capa, False)
    arquivos.append(capa)
    for n, txt in enumerate(slides, start=1):
        img = Image.new("RGB", (W, H), cores["fundo"])
        d = ImageDraw.Draw(img)
        d.text((90, 150), f"{n:02d}", font=_fonte("Fraunces-800.woff", 220), fill=cores["laranja"])
        f, linhas, lh = _titulo_que_cabe(d, txt, W - 180, 600, [86, 78, 70, 62, 56])
        y = 560
        for ln in linhas:
            d.text((90, y), ln, font=f, fill=cores["petroleo"])
            y += lh
        d.rectangle([0, H - 150, W, H], fill=cores["petroleo"])
        d.text((90, H - 75), f"Indicaê · {site}", font=_fonte("inter-latin-600-normal.woff", 34),
               fill=cores["fundo"], anchor="lm")
        d.text((W - 90, H - 75), f"{n}/{len(slides)}", font=_fonte("inter-latin-600-normal.woff", 34),
               fill=cores["fundo"], anchor="rm")
        arq = pasta / f"carrossel_{n + 1:02d}.jpg"
        img.save(arq, "JPEG", quality=92)
        arquivos.append(arq)
    # final
    img = Image.new("RGB", (W, H), cores["petroleo"])
    d = ImageDraw.Draw(img)
    d.text((W // 2, 520), "Indicaê", font=_fonte("Fraunces-800.woff", 150), fill=cores["fundo"], anchor="mm")
    d.text((W // 2, 660), "A confiança circula", font=_fonte("inter-latin-600-normal.woff", 48), fill=cores["fundo"], anchor="mm")
    d.text((W // 2, 820), "Salva este post e manda", font=_fonte("inter-latin-400-normal.woff", 42), fill=cores["fundo"], anchor="mm")
    d.text((W // 2, 880), "pra quem está precisando.", font=_fonte("inter-latin-400-normal.woff", 42), fill=cores["fundo"], anchor="mm")
    _pilula(d, W // 2 - 260, 980, f"  {site}  ", _fonte("inter-latin-700-normal.woff", 42), cores["laranja"], "#FFFFFF")
    fim = pasta / f"carrossel_{len(slides) + 2:02d}.jpg"
    img.save(fim, "JPEG", quality=92)
    arquivos.append(fim)
    return arquivos[:10]
