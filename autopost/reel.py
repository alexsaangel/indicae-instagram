"""Gera um Reel curto (9:16, ~12s) com texto animado na identidade do Indicaê.

Cenas: 1) selo + título entrando palavra por palavra  2) mensagem de apoio
3) chamada final com a marca. Usa só Pillow + ffmpeg (já vem no GitHub Actions).
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

import arte

W, H, FPS = 1080, 1920, 30


def _ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _base(cores, selo, alpha_selo=1.0):
    img = Image.new("RGB", (W, H), cores["fundo"])
    d = ImageDraw.Draw(img)
    r = 300
    d.ellipse([W - r, -r, W + r, r], fill=cores["laranja"])
    if alpha_selo > 0:
        arte._pilula(d, 90, 220, selo, arte._fonte("inter-latin-700-normal.woff", 34),
                     cores["petroleo"], cores["fundo"])
    return img, d


def _texto_palavras(d, palavras_linhas, fonte, lh, y0, mostradas, cor):
    """Desenha as palavras já reveladas, linha a linha."""
    n = 0
    y = y0
    for linha in palavras_linhas:
        x = 130
        for p in linha.split():
            if n >= mostradas:
                return
            d.text((x, y), p, font=fonte, fill=cor)
            x += d.textlength(p + " ", font=fonte)
            n += 1
        y += lh


def gerar(titulo, apoio, cores, site, selo, destino):
    tmp = Path(tempfile.mkdtemp())
    medidor = ImageDraw.Draw(Image.new("RGB", (W, H)))
    fonte, linhas, lh = arte._titulo_que_cabe(medidor, titulo, W - 260, 900, [104, 96, 88, 80, 72, 64])
    total_palavras = sum(len(l.split()) for l in linhas)
    bloco = len(linhas) * lh
    y0 = 520 + max(0, (900 - bloco) // 3)

    f_apoio, l_apoio, lh_apoio = arte._titulo_que_cabe(medidor, apoio, W - 260, 700, [64, 58, 52, 46])
    frames = []

    # Cena 1 (0–6s): título palavra por palavra
    for i in range(6 * FPS):
        img, d = _base(cores, selo)
        mostradas = int(_ease(i / (4.5 * FPS)) * total_palavras + 0.999)
        d.rectangle([90, y0 + 8, 100, y0 + bloco - 8], fill=cores["laranja"])
        _texto_palavras(d, linhas, fonte, lh, y0, mostradas, cores["petroleo"])
        frames.append(img)

    # Cena 2 (6–9.5s): mensagem de apoio
    for i in range(int(3.5 * FPS)):
        img, d = _base(cores, selo)
        k = _ease(i / (0.8 * FPS))
        y = 640 + int((1 - k) * 60)
        for ln in l_apoio:
            d.text((90, y), ln, font=f_apoio, fill=cores["petroleo"])
            y += lh_apoio
        frames.append(img)

    # Cena 3 (9.5–13s): marca + chamada
    for i in range(int(3.5 * FPS)):
        img = Image.new("RGB", (W, H), cores["petroleo"])
        d = ImageDraw.Draw(img)
        k = _ease(i / (0.8 * FPS))
        d.text((W // 2, 780 - int((1 - k) * 40)), "Indicaê", font=arte._fonte("Fraunces-800.woff", 170),
               fill=cores["fundo"], anchor="mm")
        d.text((W // 2, 930), "A confiança circula", font=arte._fonte("inter-latin-600-normal.woff", 52),
               fill=cores["fundo"], anchor="mm")
        if i > FPS:
            arte._pilula(d, W // 2 - 290, 1080, f"  {site}  ", arte._fonte("inter-latin-700-normal.woff", 44),
                         cores["laranja"], "#FFFFFF")
        frames.append(img)

    for n, f in enumerate(frames):
        f.save(tmp / f"{n:04d}.jpg", quality=90)

    destino.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    subprocess.run([
        ffmpeg, "-y", "-loglevel", "error",
        "-framerate", str(FPS), "-i", str(tmp / "%04d.jpg"),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
        str(destino),
    ], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
