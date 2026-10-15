r"""
Gera um dataset para treinar o DETECTOR de frutas (YOLO), jรก com as caixas desenhadas automaticamente.

Como: recorta as frutas das fotos do seu dataset e cola vรกrias por imagem, sobre esteiras simuladas,
inclusive ENCOSTADAS e PARCIALMENTE SOBREPOSTAS (como no vรญdeo real). Como o script sabe onde colou
cada fruta, a caixa de cada uma (sรณ a parte visรญvel) รฉ calculada sozinha: nรฃo precisa anotar nada.
O detector tem uma รบnica classe ("fruta"): quem diz qual รฉ a fruta e se estรก fresca ou estragada รฉ
o classificador, entรฃo isso funciona para todos os vegetais do seu banco de dados.

Uso (Anaconda Prompt, na pasta dos scripts):
    python gerar_dataset_deteccao.py                       # 1500 imagens com os datasets do Kaggle
    python gerar_dataset_deteccao.py --n 3000 --max-fotos 1000
    python gerar_dataset_deteccao.py --fotos "C:\fotos"     # sรณ fotos nomeadas Fruta_Estado
    python gerar_dataset_deteccao.py --fundos "C:\fundos"   # fotos da SUA esteira vazia (muito recomendado)

Saรญda: pasta dataset_detector/ (imagens, rรณtulos, data.yaml e previa_dataset.jpg para conferir).
Depois:  python treino_detector.py

Para ficar ainda melhor: grave frames da sua esteira real, anote as caixas (Roboflow, CVAT ou
LabelImg, classe "fruta") e coloque em dataset_detector/images/train e labels/train.
"""
import argparse
import hashlib
import os
import random
import sys

import cv2
import numpy as np

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:               # ao rodar cรฉlula/seleรงรฃo no Spyder, __file__ nรฃo existe
    BASE_DIR = os.getcwd()
sys.path.insert(0, BASE_DIR)

import gerar_video_esteira as g      # reaproveita leitura, recorte automรกtico e colagem

LARGURA, ALTURA = 960, 540
MIN_VISIVEL_FRAC = 0.35              # fruta com menos que isso visível (muito escondida) não vira caixa
MIN_VISIVEL_PX = 300


def salvar_imagem(caminho, img, qualidade=90):
    """Grava a imagem mesmo em caminhos com acento (cv2.imwrite falha em silรชncio nesses casos no Windows)."""
    ext = os.path.splitext(caminho)[1].lower() or ".jpg"
    params = [cv2.IMWRITE_JPEG_QUALITY, qualidade] if ext in (".jpg", ".jpeg") else []
    ok, buf = cv2.imencode(ext, img, params)
    if not ok:
        return False
    try:
        buf.tofile(caminho)
        return os.path.exists(caminho)
    except OSError:
        return False


# ------------------------------------------------------------ fotos e recortes
def coletar_todas(raizes):
    """(fruta, estado) -> lista de arquivos, de todas as classes encontradas."""
    achadas = {}
    for raiz in raizes:
        for root, _, names in os.walk(raiz):
            for n in names:
                if not n.lower().endswith(g.EXTS):
                    continue
                full = os.path.join(root, n)
                rel = os.path.relpath(full, raiz)
                estado = g.estado_do_caminho(rel)
                if estado is not None:
                    achadas.setdefault((g.fruta_do_caminho(rel), estado), []).append(full)
    return achadas


def amostrar_balanceado(achadas, maximo):
    """Sorteia fotos de forma equilibrada entre as classes (rodรญzio)."""
    filas = {k: random.sample(v, len(v)) for k, v in achadas.items()}
    escolhidas = []
    while len(escolhidas) < maximo and any(filas.values()):
        for k in list(filas):
            if filas[k] and len(escolhidas) < maximo:
                escolhidas.append(filas[k].pop())
    return escolhidas


def recorte_com_cache(caminho, pasta_cache):
    """Recorte (BGR, alfa) da fruta; guarda em PNG para nรฃo refazer o GrabCut na prรณxima vez."""
    nome = hashlib.md5(caminho.encode("utf-8")).hexdigest() + ".png"
    arq = os.path.join(pasta_cache, nome)
    if os.path.exists(arq):
        img = cv2.imdecode(np.fromfile(arq, np.uint8), cv2.IMREAD_UNCHANGED)
        if img is not None and img.ndim == 3 and img.shape[2] == 4:
            return img[..., :3].copy(), img[..., 3].copy()
    foto = g.ler_imagem(caminho)
    if foto is None:
        return None
    cor, alfa = g.recortar_fruta(foto)
    ok, buf = cv2.imencode(".png", np.dstack([cor, alfa]))
    if ok:
        buf.tofile(arq)
    return cor, alfa


# ---------------------------------------------------------------- cenรกrio
PALETA = [(58, 58, 60), (50, 52, 55), (40, 40, 42), (30, 30, 30), (120, 95, 70), (140, 125, 105),
          (70, 100, 70), (170, 170, 168), (95, 105, 120), (60, 80, 100)]       # BGR


def fundo_aleatorio(rng, fundos_reais=None):
    """Esteira simulada (ou um pedaรงo de foto sua de esteira vazia, se informada)."""
    if fundos_reais and rng.random() < 0.7:
        img = g.ler_imagem(random.choice(fundos_reais))
        if img is not None:
            h, w = img.shape[:2]
            esc = max(LARGURA / w, ALTURA / h) * rng.uniform(1.0, 1.6)
            img = cv2.resize(img, None, fx=esc, fy=esc, interpolation=cv2.INTER_AREA)
            h, w = img.shape[:2]
            x, y = int(rng.integers(0, w - LARGURA + 1)), int(rng.integers(0, h - ALTURA + 1))
            return img[y:y + ALTURA, x:x + LARGURA].copy()
    base = np.array(random.choice(PALETA), np.float32) * rng.uniform(0.85, 1.15)
    img = np.zeros((ALTURA, LARGURA, 3), np.float32) + base
    grad = np.linspace(rng.uniform(-14, 14), rng.uniform(-14, 14), LARGURA, dtype=np.float32)
    img += grad[None, :, None]                                                  # iluminaรงรฃo desigual
    ruido = cv2.resize(rng.normal(0, 6, (ALTURA // 6, LARGURA // 6)).astype(np.float32),
                       (LARGURA, ALTURA), interpolation=cv2.INTER_CUBIC)
    img += ruido[..., None] + rng.normal(0, 2.5, img.shape).astype(np.float32)
    for _ in range(int(rng.integers(30, 140))):                                 # riscos na borracha
        x0, y0 = int(rng.integers(0, LARGURA)), int(rng.integers(0, ALTURA))
        dx, dy = int(rng.integers(-40, 41)), int(rng.integers(-25, 26))
        tom = float(rng.uniform(-28, 32))
        cv2.line(img, (x0, y0), (x0 + dx, y0 + dy), tuple(float(c + tom) for c in base), 1, cv2.LINE_AA)
    img = np.clip(img, 0, 255).astype(np.uint8)
    if rng.random() < 0.7:                                                      # trilhos de metal
        for topo in (True, False):
            hb = int(ALTURA * rng.uniform(0.05, 0.13))
            tom = np.linspace(rng.uniform(150, 215), rng.uniform(110, 190), hb)
            faixa = np.repeat(tom[:, None, None], LARGURA, 1).repeat(3, 2).astype(np.uint8)
            if topo:
                img[:hb] = faixa
            else:
                img[-hb:] = faixa[::-1]
    return img


def preparar_instancia(recorte, diametro, rng):
    """Espelha, gira, ajusta cor e redimensiona o recorte de uma fruta."""
    cor, alfa = recorte
    if rng.random() < 0.5:
        cor, alfa = cv2.flip(cor, 1), cv2.flip(alfa, 1)
    h, w = alfa.shape
    ang = rng.uniform(0, 360)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    cos, sin = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    M[0, 2] += nw / 2 - w / 2
    M[1, 2] += nh / 2 - h / 2
    cor = cv2.warpAffine(cor, M, (nw, nh), flags=cv2.INTER_LINEAR)
    alfa = cv2.warpAffine(alfa, M, (nw, nh), flags=cv2.INTER_LINEAR)
    esc = diametro / max(nw, nh)
    cor = cv2.resize(cor, None, fx=esc, fy=esc, interpolation=cv2.INTER_AREA)
    alfa = cv2.resize(alfa, None, fx=esc, fy=esc, interpolation=cv2.INTER_AREA)
    cor = np.clip(cor.astype(np.float32) * rng.uniform(0.85, 1.12) + rng.uniform(-10, 10), 0, 255).astype(np.uint8)
    return cor, alfa


def gerar_cena(recortes, rng, fundos_reais):
    """Uma imagem com vรกrias frutas (algumas encostadas/sobrepostas) e suas caixas (parte visรญvel)."""
    img = fundo_aleatorio(rng, fundos_reais)
    n_itens = int(rng.integers(2, 21))
    idmap = np.full((ALTURA, LARGURA), -1, np.int32)
    colocados, areas_totais = [], {}
    for idx in range(n_itens):
        diam = LARGURA * rng.uniform(0.06, 0.13)
        cor, alfa = preparar_instancia(random.choice(recortes), diam, rng)
        h, w = alfa.shape
        raio = max(h, w) / 2
        for _ in range(15):                                    # sorteia atรฉ cair dentro da imagem
            if colocados and rng.random() < 0.75:              # perto de outra fruta -> encosta/sobrepรตe
                cx0, cy0, r0 = random.choice(colocados)
                ang = rng.uniform(0, 2 * np.pi)
                dist = (r0 + raio) * rng.uniform(0.55, 1.05)
                cx, cy = cx0 + dist * np.cos(ang), cy0 + dist * np.sin(ang)
            else:
                cx, cy = rng.uniform(0.03 * LARGURA, 0.97 * LARGURA), rng.uniform(0.06 * ALTURA, 0.94 * ALTURA)
            if 0.03 * LARGURA <= cx <= 0.97 * LARGURA and 0.06 * ALTURA <= cy <= 0.94 * ALTURA:
                break
        else:
            cx, cy = rng.uniform(0.03 * LARGURA, 0.97 * LARGURA), rng.uniform(0.06 * ALTURA, 0.94 * ALTURA)
        x, y = int(cx - w / 2), int(cy - h / 2)
        sombra = cv2.GaussianBlur(alfa, (0, 0), 4)
        g.colar(img, None, sombra, x + 4, y + 6, opac=0.25, cor_fixa=True)
        g.colar(img, cor, alfa, x, y)
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, LARGURA), min(y + h, ALTURA)
        if x0 < x1 and y0 < y1:
            regiao = alfa[y0 - y:y1 - y, x0 - x:x1 - x] > 127
            idmap[y0:y1, x0:x1][regiao] = idx
            areas_totais[idx] = int(regiao.sum())
        colocados.append((cx, cy, raio))
    caixas = []
    for idx, total in areas_totais.items():
        vis = (idmap == idx).astype(np.uint8)
        area = int(vis.sum())
        if area < MIN_VISIVEL_PX or area < MIN_VISIVEL_FRAC * total:
            continue
        x, y, bw, bh = cv2.boundingRect(vis)
        caixas.append((x, y, bw, bh))
    # acabamento: desfoque de movimento leve, ruรญdo e brilho
    if rng.random() < 0.3:
        k = int(rng.integers(3, 8))
        kern = np.zeros((k, k), np.float32)
        kern[k // 2, :] = 1.0 / k
        img = cv2.filter2D(img, -1, kern)
    img = np.clip(img.astype(np.float32) * rng.uniform(0.85, 1.15) + rng.normal(0, rng.uniform(0, 3), img.shape),
                  0, 255).astype(np.uint8)
    return img, caixas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1500, help="quantidade de imagens")
    ap.add_argument("--saida", default=os.path.join(BASE_DIR, "dataset_detector"))
    ap.add_argument("--fotos", default=None, help="pasta com fotos nomeadas Fruta_Estado.ext")
    ap.add_argument("--pasta", action="append", default=[], help="pasta de imagens de dataset (pode repetir)")
    ap.add_argument("--max-fotos", type=int, default=600, help="quantas fotos diferentes recortar")
    ap.add_argument("--fundos", default=None, help="pasta com fotos da sua esteira vazia")
    ap.add_argument("--val", type=float, default=0.1, help="fraรงรฃo de imagens de validaรงรฃo")
    ap.add_argument("--seed", type=int, default=0)
    args, _ = ap.parse_known_args()

    random.seed(args.seed)
    rng = np.random.default_rng(args.seed)

    # --- fotos de origem
    if args.fotos:
        caminhos = [arq for _, _, arq in g.carregar_fotos(args.fotos)]
    else:
        raizes = list(args.pasta)
        if not raizes:
            import kagglehub
            for slug in g.FONTES_KAGGLE:
                try:
                    raizes.append(kagglehub.dataset_download(slug))
                except Exception as e:
                    print(f"AVISO: nรฃo consegui acessar '{slug}': {e}")
        raizes = [r for r in raizes if os.path.isdir(r)]
        if not raizes:
            raise SystemExit("Nenhuma pasta de imagens disponรญvel (use --pasta ou --fotos).")
        print("Procurando imagens...")
        achadas = coletar_todas(raizes)
        caminhos = amostrar_balanceado(achadas, args.max_fotos)
    if not caminhos:
        raise SystemExit("Nenhuma foto encontrada.")

    pasta_cache = os.path.join(args.saida, "cache_recortes")
    os.makedirs(pasta_cache, exist_ok=True)
    print(f"Recortando {len(caminhos)} fotos (a primeira vez demora; depois fica em cache)...")
    recortes = []
    for i, c in enumerate(caminhos, 1):
        r = recorte_com_cache(c, pasta_cache)
        if r is not None:
            recortes.append(r)
        if i % 100 == 0:
            print(f"  {i}/{len(caminhos)}")
    if not recortes:
        raise SystemExit("Nรฃo consegui recortar nenhuma foto.")

    fundos_reais = None
    if args.fundos:
        fundos_reais = [os.path.join(args.fundos, n) for n in sorted(os.listdir(args.fundos))
                        if n.lower().endswith(g.EXTS)]
        print(f"{len(fundos_reais)} fotos de esteira vazia serรฃo usadas como fundo.")

    # --- gera as imagens
    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        os.makedirs(os.path.join(args.saida, sub), exist_ok=True)
    previas, n_caixas, falhas = [], 0, 0
    print(f"Gerando {args.n} imagens...")
    for i in range(args.n):
        img, caixas = gerar_cena(recortes, rng, fundos_reais)
        if not caixas:
            continue
        parte = "val" if rng.random() < args.val else "train"
        nome = f"cena_{i:05d}"
        if not salvar_imagem(os.path.join(args.saida, "images", parte, nome + ".jpg"), img):
            falhas += 1
            continue
        with open(os.path.join(args.saida, "labels", parte, nome + ".txt"), "w") as f:
            for x, y, bw, bh in caixas:
                f.write(f"0 {(x + bw / 2) / LARGURA:.6f} {(y + bh / 2) / ALTURA:.6f} "
                        f"{bw / LARGURA:.6f} {bh / ALTURA:.6f}\n")
        n_caixas += len(caixas)
        if len(previas) < 6:
            vis = img.copy()
            for x, y, bw, bh in caixas:
                cv2.rectangle(vis, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
            previas.append(cv2.resize(vis, (640, 360)))
        if (i + 1) % 250 == 0:
            print(f"  {i + 1}/{args.n}")

    with open(os.path.join(args.saida, "data.yaml"), "w", encoding="utf-8") as f:
        f.write(f"path: {os.path.abspath(args.saida).replace(os.sep, '/')}\n"
                "train: images/train\nval: images/val\nnames:\n  0: fruta\n")
    if previas:
        while len(previas) < 6:
            previas.append(np.zeros_like(previas[0]))
        salvar_imagem(os.path.join(args.saida, "previa_dataset.jpg"),
                      cv2.vconcat([cv2.hconcat(previas[0:2]), cv2.hconcat(previas[2:4]), cv2.hconcat(previas[4:6])]))
    n_train = len(os.listdir(os.path.join(args.saida, "images", "train")))
    n_val = len(os.listdir(os.path.join(args.saida, "images", "val")))
    if n_train == 0:
        raise SystemExit(f"ERRO: nenhuma imagem foi gravada em {args.saida}\\images\\train "
                         f"({falhas} falhas de gravaรงรฃo). Verifique permissรตes/espaรงo em disco, ou use "
                         "--saida com um caminho simples, como C:\\dataset_detector")
    if falhas:
        print(f"AVISO: {falhas} imagens nรฃo puderam ser gravadas.")
    print(f"\nPronto! {n_train} imagens de treino + {n_val} de validaรงรฃo, {n_caixas} caixas em {args.saida}")
    print("Confira previa_dataset.jpg (caixas verdes) e rode:  python treino_detector.py")


if __name__ == "__main__":
    main()
