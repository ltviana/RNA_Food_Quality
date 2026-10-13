# -*- coding: utf-8 -*-
"""
Created on Fri Oct  9 20:41:58 2026

@author: ltvia
"""

"""
Análise de frutas em uma ESTEIRA: detecta várias frutas ao mesmo tempo, identifica
qual é a fruta e se está fresca ou estragada, rastreia cada uma e conta o total.

Como funciona:
  1. Segmentação por cor: tudo que for diferente da cor da esteira vira "fruta".
  2. Cada fruta é recortada e classificada pela rede neural (todas de uma vez, em lote).
  3. Um rastreador acompanha cada fruta entre os frames e usa a média de vários frames
     (resultado mais estável). Quando a fruta sai de cena, ela entra na contagem.

Uso:
    python "Análise em Tempo Real - V2.py"                    # webcam 0
    python "Análise em Tempo Real - V2.py" --cam 1            # outra câmera
    python "Análise em Tempo Real - V2.py" --video esteira.mp4

Teclas:  q/ESC sair | b recalibrar a cor da esteira | m ver máscara |
         + / - ajustar sensibilidade | r zerar contagem
Dica: aperte 'b' com a esteira VAZIA (ou com poucas frutas) para calibrar a cor do fundo.
"""
import argparse
import json
import os
import time
from collections import defaultdict, deque
 
import cv2
import numpy as np
 
# Usa o mesmo backend do treino (PyTorch, que roda na GPU). Definir ANTES de importar o keras.
os.environ.setdefault("KERAS_BACKEND", "torch")
 
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:               # ao rodar célula/seleção no Spyder, __file__ não existe
    BASE_DIR = os.getcwd()
MODEL_PATH = os.path.join(BASE_DIR, "frutas_multiclasse.keras")
CLASSES_PATH = os.path.join(BASE_DIR, "classes_frutas.json")
 
# ------------------------------------------------------------ parâmetros
IMG_SIZE = 224
PROC_WIDTH = 960          # frames mais largos que isso são reduzidos (mais rápido)
THRESH_INIT = 28.0        # sensibilidade da segmentação (menor = detecta mais)
L_WEIGHT = 0.5            # peso do brilho na diferença de cor (reduz efeito de sombras)
MIN_AREA_FRAC = 0.004     # área mínima de uma fruta (fração da imagem)
MAX_AREA_FRAC = 0.45      # área máxima
MARGIN = 0.12             # folga ao redor da fruta no recorte
IGNORE_BORDER = True      # ignora objetos cortados pela borda (entrando/saindo da imagem)
SMOOTH = 8                # nº de frames na média por fruta
MAX_MISSED = 10           # frames sem ver a fruta antes de considerá-la "saída"
MIN_HITS = 5              # mínimo de frames vistos para entrar na contagem
MATCH_DIST_FRAC = 0.12    # distância máxima de associação entre frames (fração da largura)
LOW, HIGH = 0.35, 0.65    # faixa de incerteza para fresca/estragada
FONT = cv2.FONT_HERSHEY_SIMPLEX
 
# O OpenCV não desenha acentos; por isso os nomes em português estão sem acento.
# Frutas que não estiverem aqui aparecem com o nome original do dataset.
NOMES_PT = {
    "apple": "Maca", "banana": "Banana", "orange": "Laranja", "mango": "Manga",
    "strawberry": "Morango", "grape": "Uva", "grapes": "Uva", "pear": "Pera",
    "lemon": "Limao", "watermelon": "Melancia", "pineapple": "Abacaxi",
    "papaya": "Mamao", "peach": "Pessego", "pomegranate": "Roma", "kiwi": "Kiwi",
    "tomato": "Tomate", "potato": "Batata", "carrot": "Cenoura", "cucumber": "Pepino",
    "bellpepper": "Pimentao", "capsicum": "Pimentao", "okra": "Quiabo", "guava": "Goiaba",
    "jujube": "Jujuba", "bittergourd": "Melao amargo",
}
 
 
def nome_pt(fruta):
    return NOMES_PT.get(fruta.lower(), fruta)
 
 
# ----------------------------------------------------------- segmentação
def calibrar_esteira(frame):
    """Cor da esteira = mediana da imagem em Lab (funciona se as frutas cobrem < 50%)."""
    lab = cv2.cvtColor(cv2.GaussianBlur(frame, (7, 7), 0), cv2.COLOR_BGR2LAB).astype(np.float32)
    return np.median(lab.reshape(-1, 3), axis=0)
 
 
def segmentar(frame, esteira_lab, limiar):
    lab = cv2.cvtColor(cv2.GaussianBlur(frame, (7, 7), 0), cv2.COLOR_BGR2LAB).astype(np.float32)
    d = lab - esteira_lab
    d[..., 0] *= L_WEIGHT
    dist = np.sqrt((d ** 2).sum(axis=2))
    mask = (dist > limiar).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)), iterations=2)
    return mask
 
 
def encontrar_frutas(mask):
    h, w = mask.shape[:2]
    contornos, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    caixas = []
    for c in contornos:
        area = cv2.contourArea(c)
        if area < MIN_AREA_FRAC * h * w or area > MAX_AREA_FRAC * h * w:
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        if IGNORE_BORDER and (x <= 2 or y <= 2 or x + bw >= w - 2 or y + bh >= h - 2):
            continue
        caixas.append((x, y, bw, bh))
    return caixas
 
 
def recorte_quadrado(frame, caixa):
    h, w = frame.shape[:2]
    x, y, bw, bh = caixa
    lado = int(max(bw, bh) * (1 + 2 * MARGIN))
    x0, y0 = int(x + bw / 2 - lado / 2), int(y + bh / 2 - lado / 2)
    x1, y1 = x0 + lado, y0 + lado
    crop = frame[max(0, y0):min(h, y1), max(0, x0):min(w, x1)]
    pads = (max(0, -y0), max(0, y1 - h), max(0, -x0), max(0, x1 - w))
    if any(pads):
        crop = cv2.copyMakeBorder(crop, *pads, cv2.BORDER_REPLICATE)
    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    return cv2.resize(rgb, (IMG_SIZE, IMG_SIZE))
 
 
def centro(caixa):
    x, y, bw, bh = caixa
    return np.array([x + bw / 2, y + bh / 2], dtype=np.float32)
 
 
# ---------------------------------------------------------- rastreamento
class Fruta:
    def __init__(self, tid, caixa, probs):
        self.id = tid
        self.caixa = caixa
        self.c = centro(caixa)
        self.v = np.zeros(2, dtype=np.float32)      # velocidade estimada (px/frame)
        self.hist = deque([probs], maxlen=SMOOTH)
        self.hits = 1
        self.perdida = 0
 
    def prever(self):
        return self.c + self.v
 
    def atualizar(self, caixa, probs):
        novo = centro(caixa)
        self.v = 0.5 * self.v + 0.5 * (novo - self.c)
        self.c, self.caixa = novo, caixa
        self.hist.append(probs)
        self.hits += 1
        self.perdida = 0
 
    def probs_medias(self):
        return np.mean(self.hist, axis=0)
 
 
class Rastreador:
    def __init__(self, dist_max, ao_finalizar):
        self.itens, self.prox_id = [], 1
        self.dist_max, self.ao_finalizar = dist_max, ao_finalizar
 
    def atualizar(self, caixas, probs_lista):
        pares = []
        for ti, t in enumerate(self.itens):
            p = t.prever()
            for di, cx in enumerate(caixas):
                d = float(np.linalg.norm(p - centro(cx)))
                if d <= self.dist_max:
                    pares.append((d, ti, di))
        usados_t, usados_d = set(), set()
        for d, ti, di in sorted(pares):
            if ti in usados_t or di in usados_d:
                continue
            self.itens[ti].atualizar(caixas[di], probs_lista[di])
            usados_t.add(ti)
            usados_d.add(di)
        for ti, t in enumerate(self.itens):
            if ti not in usados_t:
                t.perdida += 1
        for di, cx in enumerate(caixas):
            if di not in usados_d:
                self.itens.append(Fruta(self.prox_id, cx, probs_lista[di]))
                self.prox_id += 1
        vivos = []
        for t in self.itens:
            if t.perdida > MAX_MISSED:
                if t.hits >= MIN_HITS:
                    self.ao_finalizar(t)
            else:
                vivos.append(t)
        self.itens = vivos
 
    def finalizar_todos(self):
        for t in self.itens:
            if t.hits >= MIN_HITS:
                self.ao_finalizar(t)
        self.itens = []
 
 
# ---------------------------------------------------------- classificação
def carregar_classes(caminho):
    with open(caminho, encoding="utf-8") as f:
        info = json.load(f)["classes"]
    frutas = sorted({c["fruit"] for c in info})
    mat = np.zeros((len(info), len(frutas)), dtype=np.float32)   # classe -> fruta
    for i, c in enumerate(info):
        mat[i, frutas.index(c["fruit"])] = 1.0
    estragada = np.array([c["rotten"] for c in info], dtype=bool)
    return frutas, mat, estragada
 
 
def interpretar(probs, frutas, mat, estragada):
    """Soma as probabilidades por fruta e por estado -> (fruta, conf. da fruta, P(estragada))."""
    pf = probs @ mat
    i = int(pf.argmax())
    return frutas[i], float(pf[i]), float(probs[estragada].sum())
 
 
def veredito(p_estragada):
    if p_estragada >= HIGH:
        return "ESTRAGADA", (0, 0, 255), p_estragada
    if p_estragada <= LOW:
        return "FRESCA", (0, 180, 0), 1 - p_estragada
    return "INCERTO", (0, 200, 255), max(p_estragada, 1 - p_estragada)
 
 
def desenhar_rotulo(img, x, y, texto, cor):
    (tw, th), _ = cv2.getTextSize(texto, FONT, 0.55, 2)
    y0 = max(0, y - th - 10)
    cv2.rectangle(img, (x, y0), (x + tw + 8, y0 + th + 10), cor, -1)
    cv2.putText(img, texto, (x + 4, y0 + th + 3), FONT, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
 
 
# ----------------------------------------------------------------- vídeo
def resolver_video(caminho):
    """Procura o vídeo no caminho informado e na pasta do script.
    No Windows, se o caminho tiver acentos, usa o nome curto (ASCII), que o OpenCV abre melhor."""
    for c in (caminho, os.path.join(BASE_DIR, caminho)):
        if os.path.isfile(c):
            c = os.path.abspath(c)
            if os.name == "nt" and not c.isascii():
                try:
                    import ctypes
                    buf = ctypes.create_unicode_buffer(1024)
                    if ctypes.windll.kernel32.GetShortPathNameW(c, buf, 1024) and buf.value.isascii():
                        return buf.value
                except Exception:
                    pass
            return c
    return None
 
 
# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--video", default=None, help="arquivo de vídeo (em vez da webcam)")
    ap.add_argument("--model", default=MODEL_PATH)
    ap.add_argument("--classes", default=CLASSES_PATH)
    ap.add_argument("--thresh", type=float, default=THRESH_INIT)
    args, _ = ap.parse_known_args()   # ignora argumentos extras injetados pelo Spyder/IPython
 
    for p in (args.model, args.classes):
        if not os.path.exists(p):
            raise SystemExit(f"Arquivo não encontrado:\n  {p}\n"
                             "Rode antes o treino_multiclasse.py até o fim.")
 
    fonte = args.cam
    if args.video:
        fonte = resolver_video(args.video)
        if fonte is None:
            raise SystemExit(
                f"Vídeo não encontrado: {args.video}\n"
                f"Procurei em:\n  {os.path.abspath(args.video)}\n  {os.path.join(BASE_DIR, args.video)}\n"
                'Confira o nome/extensão do arquivo ou informe o caminho completo, '
                'por exemplo: --video "C:\\videos\\minha_esteira.mp4"')
 
    import keras   # importado aqui para o backend já estar definido
    model = keras.models.load_model(args.model)
    frutas, mat, estragada = carregar_classes(args.classes)
    print("Backend do Keras:", keras.config.backend())
    print("Frutas conhecidas:", ", ".join(frutas))
 
    def prever(crops):
        X = np.stack(crops).astype("float32")           # RGB 0-255; normalização está no modelo
        return keras.ops.convert_to_numpy(model(X, training=False))
 
    cap = cv2.VideoCapture(fonte)
    if not cap.isOpened():
        if args.video:
            raise SystemExit(
                f"O vídeo existe, mas o OpenCV não conseguiu abri-lo:\n  {fonte}\n"
                "Causas comuns: codec incomum (converta para MP4/H.264, por exemplo com o "
                "VLC ou o HandBrake) ou caminho com acentos (copie o vídeo para uma pasta "
                "simples, como C:\\videos).")
        raise SystemExit("Não consegui abrir a câmera. Verifique as permissões do "
                         "sistema e se outro programa não está usando a câmera.")
 
    totais = defaultdict(lambda: [0, 0])    # fruta -> [frescas, estragadas]
    incertos = [0]
 
    def ao_finalizar(f):
        fruta, _, p_est = interpretar(f.probs_medias(), frutas, mat, estragada)
        if p_est >= HIGH:
            totais[fruta][1] += 1
        elif p_est <= LOW:
            totais[fruta][0] += 1
        else:
            incertos[0] += 1
 
    esteira_lab, rastreador = None, None
    recalibrar = True
    limiar, ver_mascara = args.thresh, False
    prev, fps = time.time(), 0.0
 
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame.shape[1] > PROC_WIDTH:
                esc = PROC_WIDTH / frame.shape[1]
                frame = cv2.resize(frame, None, fx=esc, fy=esc, interpolation=cv2.INTER_AREA)
            h, w = frame.shape[:2]
            if recalibrar:                      # calibra com o frame ainda sem desenhos
                esteira_lab = calibrar_esteira(frame)
                recalibrar = False
            if rastreador is None:
                rastreador = Rastreador(MATCH_DIST_FRAC * w, ao_finalizar)
 
            mask = segmentar(frame, esteira_lab, limiar)
            caixas = encontrar_frutas(mask)
            probs = list(prever([recorte_quadrado(frame, cx) for cx in caixas])) if caixas else []
            rastreador.atualizar(caixas, probs)
 
            # desenha as frutas visíveis neste frame
            for f in rastreador.itens:
                if f.perdida > 0:
                    continue
                fruta, conf_fruta, p_est = interpretar(f.probs_medias(), frutas, mat, estragada)
                estado, cor, conf = veredito(p_est)
                x, y, bw, bh = f.caixa
                cv2.rectangle(frame, (x, y), (x + bw, y + bh), cor, 3)
                nome = nome_pt(fruta) + ("?" if conf_fruta < 0.5 else "")
                desenhar_rotulo(frame, x, y, f"#{f.id} {nome} | {estado} {conf * 100:.0f}%", cor)
 
            # painel de contagem
            linhas = [f"{nome_pt(fr)}: {v[0]} frescas | {v[1]} estragadas"
                      for fr, v in sorted(totais.items())]
            linhas.append(f"Incertos: {incertos[0]}")
            altura = 34 + 22 * len(linhas)
            painel = frame.copy()
            cv2.rectangle(painel, (0, 0), (360, altura), (0, 0, 0), -1)
            frame = cv2.addWeighted(painel, 0.6, frame, 0.4, 0)
            cv2.putText(frame, "CONTAGEM", (10, 22), FONT, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            for i, t in enumerate(linhas):
                cv2.putText(frame, t, (10, 46 + 22 * i), FONT, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
 
            agora = time.time()
            fps = 0.9 * fps + 0.1 * (1 / max(agora - prev, 1e-6))
            prev = agora
            cv2.putText(frame, f"{fps:.0f} FPS | sens {limiar:.0f}", (w - 190, 25),
                        FONT, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
 
            cv2.imshow("Esteira de frutas", frame)
            if ver_mascara:
                cv2.imshow("Mascara", mask)
 
            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (ord("q"), 27):
                break
            elif tecla == ord("b"):
                recalibrar = True
            elif tecla == ord("m"):
                ver_mascara = not ver_mascara
                if not ver_mascara:
                    cv2.destroyWindow("Mascara")
            elif tecla in (ord("+"), ord("=")):
                limiar += 2
            elif tecla in (ord("-"), ord("_")):
                limiar = max(4, limiar - 2)
            elif tecla == ord("r"):
                totais.clear()
                incertos[0] = 0
    finally:
        # sempre libera a câmera e fecha as janelas, mesmo se der erro
        cap.release()
        cv2.destroyAllWindows()
        for _ in range(5):
            cv2.waitKey(1)
        if rastreador is not None:
            rastreador.finalizar_todos()
        print("\nResumo da contagem:")
        for fr, v in sorted(totais.items()):
            print(f"  {fr}: {v[0]} frescas, {v[1]} estragadas")
        print(f"  Incertos: {incertos[0]}")
 
 
if __name__ == "__main__":
    main()