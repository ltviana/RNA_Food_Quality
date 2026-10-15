r"""
Esteira v3 - detecta cada fruta (mesmo encostadas/parcialmente sobrepostas), classifica fresca ou
estragada e CONTA somente o vegetal escolhido pelo usuário.

Como funciona
  1. Detector: YOLO (ultralytics) encontra cada fruta individualmente, mesmo com sobreposição parcial.
     Se não houver YOLO, usa o detector antigo por cor (só serve para frutas separadas e fundo liso).
  2. Rastreador: acompanha cada fruta entre os frames (número #id) e usa a média de várias leituras.
  3. Classificador: a rede neural lê cada fruta em SEGUNDO PLANO (outra thread), poucas por frame e em
     lote de tamanho fixo. O vídeo nunca espera pela rede -> o FPS não cai quando entram frutas novas.
  4. Contagem: cada fruta que passa é identificada (qual vegetal é) e entra na contagem de
     frescos e estragados do SEU tipo. O painel mostra o total por vegetal.

Uso (Anaconda Prompt, na pasta dos scripts):
    python esteira.py                                 # webcam, conta todos os vegetais
    python esteira.py --video video.mp4               # com um vídeo
    python esteira.py --video video.mp4 --fruta Apple # (opcional) conta só um vegetal
    python esteira.py --video video.mp4 --fornecedor "Fazenda X"   # grava a contagem no banco do app_frutas.py
    python esteira.py --video video.mp4 --tempo-real  # no ritmo do vídeo (descarta frames atrasados)
    python esteira.py --video video.mp4 --sem-janela  # teste de velocidade, sem abrir janela

Teclas: q/ESC sair | o marcar a área da esteira |
        r zerar contagem | (detector por cor) b recalibrar, m máscara, + / - sensibilidade
"""
import argparse
import contextlib
import json
import os
import queue
import re
import threading
import time
import unicodedata
from collections import deque

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
DET_PESOS_PROPRIOS = os.path.join(BASE_DIR, "fruta_detector.pt")   # gerado por treino_detector.py
DET_PESOS_COCO = "yolo11n.pt"                                      # baixado automaticamente

# ------------------------------------------------------------ parâmetros
IMG_SIZE = 224
PROC_WIDTH = 960          # a detecção usa frames reduzidos a esta largura (os recortes usam o original)
DET_IMGSZ = 640           # tamanho de entrada do YOLO
DET_CONF = 0.35           # confiança mínima do detector
DET_IOU = 0.5             # sobreposição máxima entre caixas do mesmo objeto
CLASSES_COCO = {"banana", "apple", "orange", "broccoli", "carrot"}   # usadas se o YOLO for o COCO
MARGEM_CROP = 0.08        # folga ao redor da fruta no recorte enviado ao classificador
FUNDO_MASCARA = 255       # cor que apaga vizinhos nos cantos do recorte (255 = branco)
LOTE_FIXO = 8             # a rede sempre recebe lotes deste tamanho (sem realocar na GPU)
MAX_CROPS_FRAME = 4       # no máximo estas frutas são enviadas à rede por frame
N_INICIAL = 4             # leituras seguidas em cada fruta nova
INTERVALO_CLS = 8         # depois, relê a fruta a cada N frames (a oclusão muda com o tempo)
SMOOTH = 8                # nº de leituras na média de cada fruta
MAX_PERDIDA = 10          # frames sem ver a fruta antes de considerá-la "saída"
MIN_HITS = 5              # mínimo de frames vistos para entrar na contagem
MIN_CLS = 3               # mínimo de leituras da rede para entrar na contagem
LOW, HIGH = 0.35, 0.65    # faixa de incerteza para fresca/estragada

FONT = cv2.FONT_HERSHEY_SIMPLEX

# parâmetros do detector por cor (antigo)
THRESH_INIT = 28.0        # sensibilidade da segmentação (menor = detecta mais)
L_WEIGHT = 0.5            # peso do brilho na diferença de cor (reduz efeito de sombras)
MIN_AREA_FRAC = 0.004     # área mínima de uma fruta (fração da imagem)
MAX_AREA_FRAC = 0.45      # área máxima
IGNORE_BORDER = True      # ignora objetos cortados pela borda

# O OpenCV não desenha acentos; por isso os nomes em português estão sem acento.
NOMES_PT = {
    "apple": "Maca", "banana": "Banana", "orange": "Laranja", "mango": "Manga",
    "strawberry": "Morango", "grape": "Uva", "grapes": "Uva", "pear": "Pera",
    "lemon": "Limao", "watermelon": "Melancia", "pineapple": "Abacaxi",
    "papaya": "Mamao", "peach": "Pessego", "pomegranate": "Roma", "kiwi": "Kiwi",
    "tomato": "Tomate", "potato": "Batata", "carrot": "Cenoura", "cucumber": "Pepino",
    "bellpepper": "Pimentao", "capsicum": "Pimentao", "okra": "Quiabo", "guava": "Goiaba",
    "jujube": "Jujuba", "bittergourd": "Melao amargo", "broccoli": "Brocolis",
}


def nome_pt(fruta):
    return NOMES_PT.get(fruta.lower(), fruta)


def sem_acentos(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


# ------------------------------------------- detector antigo (por cor)
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


class DetectorCor:
    """Detector antigo: tudo que difere da cor da esteira vira uma fruta. NÃO separa frutas encostadas."""
    nome = "cor"

    def __init__(self, limiar):
        self.limiar, self.esteira_lab, self.recalibrar, self.mask = limiar, None, True, None

    def detectar(self, frame):
        if self.recalibrar or self.esteira_lab is None:
            self.esteira_lab, self.recalibrar = calibrar_esteira(frame), False
        self.mask = segmentar(frame, self.esteira_lab, self.limiar)
        return [(x, y, w, h, 1.0) for x, y, w, h in encontrar_frutas(self.mask)]


class DetectorYOLO:
    """YOLO (ultralytics): uma caixa por fruta, mesmo com sobreposição parcial."""
    nome = "yolo"

    def __init__(self, pesos, conf=DET_CONF, imgsz=DET_IMGSZ):
        from ultralytics import YOLO
        try:
            import torch
            cuda = torch.cuda.is_available()
        except ImportError:
            cuda = False
        self.modelo = YOLO(pesos)
        self.pesos, self.conf, self.imgsz = pesos, conf, imgsz
        self.device, self.half = (0 if cuda else "cpu"), cuda
        nomes = self.modelo.names                       # {id: nome}
        self.classes = None
        if len(nomes) > 1:                              # YOLO COCO (80 classes): só as frutas
            ids = [i for i, n in nomes.items() if str(n).lower() in CLASSES_COCO]
            self.classes = ids or None

    def detectar(self, frame):
        r = self.modelo.predict(frame, imgsz=self.imgsz, conf=self.conf, iou=DET_IOU,
                                classes=self.classes, device=self.device, half=self.half,
                                verbose=False)[0]
        if r.boxes is None or len(r.boxes) == 0:
            return []
        xyxy = r.boxes.xyxy.cpu().numpy()
        conf = r.boxes.conf.cpu().numpy()
        return [(int(x0), int(y0), int(x1 - x0), int(y1 - y0), float(c))
                for (x0, y0, x1, y1), c in zip(xyxy, conf)]


def criar_detector(modo, pesos, limiar):
    """auto: detector próprio (fruta_detector.pt) > YOLO COCO > detector por cor."""
    padrao = pesos or (DET_PESOS_PROPRIOS if os.path.exists(DET_PESOS_PROPRIOS) else DET_PESOS_COCO)
    if modo == "cor":
        return DetectorCor(limiar)
    if modo == "yolo":
        return DetectorYOLO(padrao)
    try:
        return DetectorYOLO(padrao)
    except Exception as e:
        print(f"AVISO: YOLO indisponível ({type(e).__name__}: {e}).\n"
              "       Para frutas encostadas instale com:  python -m pip install ultralytics\n"
              "       Usando o detector por cor (não separa frutas encostadas).")
        return DetectorCor(limiar)


# ---------------------------------------------------------- rastreamento
def centro(caixa):
    x, y, bw, bh = caixa[:4]
    return np.array([x + bw / 2, y + bh / 2], dtype=np.float32)


def toca_borda(caixa, w, h, folga=3):
    x, y, bw, bh = caixa[:4]
    return x <= folga or y <= folga or x + bw >= w - folga or y + bh >= h - folga


class Fruta:
    def __init__(self, tid, caixa):
        self.id, self.caixa, self.c = tid, tuple(caixa[:4]), centro(caixa)
        self.v = np.zeros(2, dtype=np.float32)          # velocidade estimada (px/frame)
        self.hist = deque(maxlen=SMOOTH)                # últimas leituras da rede (probabilidades)
        self.hits, self.perdida = 1, 0
        self.n_cls, self.ultimo_cls, self.pendente = 0, -999, False

    def tamanho(self):
        return float((self.caixa[2] * self.caixa[3]) ** 0.5)

    def prever(self):
        return self.c + self.v

    def atualizar(self, caixa):
        novo = centro(caixa)
        self.v = 0.5 * self.v + 0.5 * (novo - self.c)
        self.c, self.caixa = novo, tuple(caixa[:4])
        self.hits += 1
        self.perdida = 0

    def add_probs(self, probs, frame_idx):
        self.hist.append(probs)
        self.n_cls += 1
        self.ultimo_cls, self.pendente = frame_idx, False

    def probs_medias(self):
        return np.mean(self.hist, axis=0) if self.hist else None

    def pronta(self):
        return self.n_cls >= MIN_CLS


class Rastreador:
    def __init__(self, largura, ao_finalizar):
        self.itens, self.prox_id, self.mapa = [], 1, {}
        self.largura, self.ao_finalizar = largura, ao_finalizar

    def atualizar(self, caixas):
        pares = []
        for ti, t in enumerate(self.itens):
            p, gate = t.prever(), max(1.0 * t.tamanho(), 0.05 * self.largura)
            for di, cx in enumerate(caixas):
                d = float(np.linalg.norm(p - centro(cx)))
                if d <= gate:
                    pares.append((d, ti, di))
        usados_t, usados_d = set(), set()
        for d, ti, di in sorted(pares):
            if ti in usados_t or di in usados_d:
                continue
            self.itens[ti].atualizar(caixas[di])
            usados_t.add(ti)
            usados_d.add(di)
        for ti, t in enumerate(self.itens):
            if ti not in usados_t:
                t.perdida += 1
        for di, cx in enumerate(caixas):
            if di not in usados_d:
                self.itens.append(Fruta(self.prox_id, cx))
                self.prox_id += 1
        vivos = []
        for t in self.itens:
            if t.perdida > MAX_PERDIDA:
                if t.hits >= MIN_HITS and t.pronta():
                    self.ao_finalizar(t)
            else:
                vivos.append(t)
        self.itens = vivos
        self.mapa = {t.id: t for t in vivos}

    def finalizar_todos(self):
        for t in self.itens:
            if t.hits >= MIN_HITS and t.pronta():
                self.ao_finalizar(t)
        self.itens, self.mapa = [], {}


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


def recortar_para_modelo(frame, caixa, escala, usar_mascara=True):
    """Recorta a fruta do frame ORIGINAL (maior resolução). Em frutas redondas, os cantos do recorte
    (onde ficam pedaços das vizinhas) são apagados com uma elipse."""
    x, y, bw, bh = [v / escala for v in caixa[:4]]
    H, W = frame.shape[:2]
    lado = max(2, int(round(max(bw, bh) * (1 + 2 * MARGEM_CROP))))
    x0, y0 = int(round(x + bw / 2 - lado / 2)), int(round(y + bh / 2 - lado / 2))
    x1, y1 = x0 + lado, y0 + lado
    crop = frame[max(0, y0):min(H, y1), max(0, x0):min(W, x1)]
    pads = (max(0, -y0), max(0, y1 - H), max(0, -x0), max(0, x1 - W))
    if any(pads):
        crop = cv2.copyMakeBorder(crop, *pads, cv2.BORDER_REPLICATE)
    if usar_mascara and bh > 0 and 0.75 <= bw / bh <= 1.33:
        m = np.zeros(crop.shape[:2], np.uint8)
        cv2.ellipse(m, (crop.shape[1] // 2, crop.shape[0] // 2),
                    (max(1, int(bw / 2 * 1.06)), max(1, int(bh / 2 * 1.06))), 0, 0, 360, 255, -1)
        crop = np.where(m[..., None] > 0, crop, FUNDO_MASCARA).astype(np.uint8)
    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    interp = cv2.INTER_AREA if lado > IMG_SIZE else cv2.INTER_LINEAR
    return cv2.resize(rgb, (IMG_SIZE, IMG_SIZE), interpolation=interp)


def criar_prever(caminho_modelo, lote=LOTE_FIXO):
    """Carrega o modelo e devolve prever(lista_de_recortes) -> probabilidades.
    Sempre usa lotes do mesmo tamanho (preenchidos com zeros) e meia precisão na GPU (se confiável)."""
    import keras
    try:
        import torch
    except ImportError:
        torch = None
    cuda = bool(torch is not None and torch.cuda.is_available())
    if cuda:
        torch.backends.cudnn.benchmark = True            # escolhe os melhores kernels (formato fixo)
    modelo = keras.models.load_model(caminho_modelo)

    def _fwd(X, amp):
        ctx = torch.inference_mode() if torch is not None else contextlib.nullcontext()
        with ctx:
            if amp:
                with torch.autocast("cuda", dtype=torch.float16):
                    out = modelo(X, training=False)
            else:
                out = modelo(X, training=False)
        return keras.ops.convert_to_numpy(out).astype("float32")

    teste = np.random.default_rng(0).uniform(0, 255, (lote, IMG_SIZE, IMG_SIZE, 3)).astype("float32")
    ref = _fwd(teste, False)
    amp = False
    if cuda:
        try:
            amp = float(np.abs(ref - _fwd(teste, True)).max()) < 0.05    # só usa fp16 se bater com fp32
        except Exception:
            amp = False
    for _ in range(3):                                   # aquece (cudnn, alocações)
        _fwd(teste, amp)
    print(f"Classificador pronto (lote fixo {lote}, GPU={'sim' if cuda else 'não'}, "
          f"meia precisão={'sim' if amp else 'não'})")

    def prever(crops):
        n, saidas = len(crops), []
        for i in range(0, n, lote):
            bloco = crops[i:i + lote]
            X = np.zeros((lote, IMG_SIZE, IMG_SIZE, 3), np.float32)
            X[:len(bloco)] = np.asarray(bloco, np.float32)
            saidas.append(_fwd(X, amp)[:len(bloco)])
        return np.concatenate(saidas, axis=0) if saidas else np.zeros((0, 1), np.float32)

    return prever


class ClassificadorAsync:
    """Roda a rede em outra thread: o laço de vídeo só envia recortes e recolhe resultados."""
    def __init__(self, prever):
        self.prever = prever
        self.entrada, self.saida = queue.Queue(maxsize=2), queue.Queue()
        self.t_medio, self._ocupado, self._parar = 0.0, False, False
        self.th = threading.Thread(target=self._loop, daemon=True)
        self.th.start()

    def _loop(self):
        while not self._parar:
            try:
                ids, crops = self.entrada.get(timeout=0.1)
            except queue.Empty:
                continue
            self._ocupado = True
            t0 = time.perf_counter()
            try:
                probs = self.prever(crops)
                self.t_medio = 0.9 * self.t_medio + 0.1 * (time.perf_counter() - t0) * 1000
                self.saida.put((ids, probs))
            except Exception as e:                       # repassa o erro para o laço principal
                self.saida.put((None, e))
            self._ocupado = False

    def enviar(self, ids, crops):
        try:
            self.entrada.put_nowait((ids, crops))
            return True
        except queue.Full:
            return False

    def coletar(self):
        res = []
        while True:
            try:
                ids, probs = self.saida.get_nowait()
            except queue.Empty:
                return res
            if ids is None:
                raise RuntimeError(f"Erro no classificador: {probs}")
            res.append((ids, probs))

    def fila(self):
        return self.entrada.qsize() + int(self._ocupado)

    def esperar(self, timeout=3.0):
        fim = time.time() + timeout
        while self.fila() and time.time() < fim:
            time.sleep(0.01)

    def encerrar(self):
        self._parar = True
        self.th.join(timeout=2)


class ClassificadorSync:
    """Mesma interface, mas bloqueia o vídeo (como era antes). Serve para comparar a velocidade."""
    def __init__(self, prever):
        self.prever, self.saida, self.t_medio = prever, [], 0.0

    def enviar(self, ids, crops):
        t0 = time.perf_counter()
        self.saida.append((ids, self.prever(crops)))
        self.t_medio = 0.9 * self.t_medio + 0.1 * (time.perf_counter() - t0) * 1000
        return True

    def coletar(self):
        res, self.saida = self.saida, []
        return res

    def fila(self):
        return 0

    def esperar(self, timeout=0):
        pass

    def encerrar(self):
        pass


def escolher_para_classificar(itens, frame_idx, w, h):
    """Quais frutas enviar à rede neste frame: novas primeiro; as já lidas, de tempos em tempos."""
    cand = []
    for t in itens:
        if t.perdida > 0 or t.pendente or toca_borda(t.caixa, w, h):
            continue
        if t.n_cls < N_INICIAL or frame_idx - t.ultimo_cls >= INTERVALO_CLS:
            cand.append(t)
    cand.sort(key=lambda t: (t.n_cls, t.ultimo_cls))
    return cand[:MAX_CROPS_FRAME]


# ------------------------------------------------------- vídeo / entrada
class Leitor:
    """Lê os frames em outra thread. Câmera e --tempo-real: guarda só o frame mais recente."""
    def __init__(self, cap, descartar, simular_relogio=False, fps=30.0):
        self.cap, self.descartar, self.simular, self.fps = cap, descartar, simular_relogio, fps
        self.q = queue.Queue(maxsize=1 if descartar else 4)
        self.fim, self.parar, self.descartados = False, False, 0
        self.th = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self.th.start()

    def _loop(self):
        t0, i = time.perf_counter(), 0
        while not self.parar:
            ok, f = self.cap.read()
            if not ok:
                break
            if self.simular:                              # entrega no ritmo original do vídeo
                esp = t0 + i / self.fps - time.perf_counter()
                if esp > 0:
                    time.sleep(esp)
                i += 1
            if self.descartar:
                try:
                    self.q.get_nowait()
                    self.descartados += 1
                except queue.Empty:
                    pass
                self.q.put(f)
            else:
                while not self.parar:
                    try:
                        self.q.put(f, timeout=0.1)
                        break
                    except queue.Full:
                        continue
        self.fim = True

    def ler(self, timeout=0.5):
        while True:
            try:
                return self.q.get(timeout=timeout)
            except queue.Empty:
                if self.fim and self.q.empty():
                    return None

    def encerrar(self):
        self.parar = True
        self.th.join(timeout=2)


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


def ler_gabarito(video, fruta):
    """Se existir <video>_gabarito.txt (criado pelo gerar_video_esteira.py), devolve (frescas, estragadas)."""
    for base in (video, os.path.join(BASE_DIR, video)):
        arq = os.path.splitext(base)[0] + "_gabarito.txt"
        if os.path.exists(arq):
            with open(arq, encoding="utf-8") as f:
                for linha in f:
                    m = re.match(r"\s*(\w+):\s*(\d+) frescas, (\d+) estragadas", linha)
                    if m and m.group(1).lower() == fruta.lower():
                        return int(m.group(2)), int(m.group(3))
    return None


# ------------------------------------------------ filtro opcional (--fruta)
def resolver_fruta(texto, validas):
    alvo = sem_acentos(texto).lower().strip()
    for f in validas:
        if alvo in (f.lower(), sem_acentos(nome_pt(f)).lower()):
            return f
    return None


# ----------------------------------------------------------------- main
def resumo_texto(fruta, v, gab=None):
    linha = f"  {fruta}: {v[0]} frescos, {v[1]} estragados" + (f", {v[2]} incertos" if v[2] else "")
    if gab is not None:
        linha += f"   | esperado (gabarito): {gab[0]} frescos, {gab[1]} estragados"
    return linha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--video", default=None, help="arquivo de vídeo (em vez da webcam)")
    ap.add_argument("--fornecedor", default=None,
                    help="nome (ou id) do fornecedor: ao terminar, grava a contagem no banco do app_frutas.py")
    ap.add_argument("--referencia", default="", help="nota fiscal / nº da carga, gravado junto com a contagem")
    ap.add_argument("--fruta", default=None, help="(opcional) conta apenas este vegetal; por padrão conta todos")
    ap.add_argument("--model", default=MODEL_PATH)
    ap.add_argument("--classes", default=CLASSES_PATH)
    ap.add_argument("--detector", choices=("auto", "yolo", "cor"), default="auto")
    ap.add_argument("--det-pesos", default=None, help="pesos do YOLO (padrão: fruta_detector.pt ou yolo11n.pt)")
    ap.add_argument("--thresh", type=float, default=THRESH_INIT, help="sensibilidade do detector por cor")
    ap.add_argument("--roi", default=None, help="área da esteira em frações: x0,y0,x1,y1 (ex.: 0,0.15,1,0.95)")
    ap.add_argument("--tempo-real", action="store_true", help="vídeo no ritmo original, descartando frames atrasados")
    ap.add_argument("--sincrono", action="store_true", help="classifica no laço principal (só para comparar a velocidade)")
    ap.add_argument("--sem-mascara", action="store_true", help="não apaga os cantos do recorte")
    ap.add_argument("--arquivo-parar", default=None,
                    help="se este arquivo aparecer, a esteira encerra, grava a contagem e sai (usado pelo app_frutas.py)")
    ap.add_argument("--sem-janela", action="store_true", help="não abre janela (teste de velocidade)")
    args, _ = ap.parse_known_args()   # ignora argumentos extras injetados pelo Spyder/IPython

    for p in (args.model, args.classes):
        if not os.path.exists(p):
            raise SystemExit(f"Arquivo não encontrado:\n  {p}\nRode antes o treino_multiclasse.py até o fim.")
    fonte = args.cam
    if args.video:
        fonte = resolver_video(args.video)
        if fonte is None:
            raise SystemExit(
                f"Vídeo não encontrado: {args.video}\n"
                f"Procurei em:\n  {os.path.abspath(args.video)}\n  {os.path.join(BASE_DIR, args.video)}\n"
                'Confira o nome/extensão do arquivo ou informe o caminho completo, '
                'por exemplo: --video "C:\\videos\\minha_esteira.mp4"')

    frutas, mat, estragada = carregar_classes(args.classes)
    filtro = None
    if args.fruta:
        filtro = resolver_fruta(args.fruta, frutas)
        if filtro is None:
            raise SystemExit(f"Vegetal '{args.fruta}' desconhecido. Opções: {', '.join(frutas)}")
    print("Vegetais reconhecidos:", ", ".join(nome_pt(f) for f in frutas)
          + (f" | contando só: {nome_pt(filtro)}" if filtro else ""))

    # --- detector, classificador e câmera/vídeo
    detector = criar_detector(args.detector, args.det_pesos, args.thresh)
    print(f"Detector: {detector.nome}" + (f" ({detector.pesos})" if detector.nome == "yolo" else ""))
    prever = criar_prever(args.model)
    clf = ClassificadorSync(prever) if args.sincrono else ClassificadorAsync(prever)
    cap = cv2.VideoCapture(fonte)
    if not cap.isOpened():
        clf.encerrar()
        if args.video:
            raise SystemExit(
                f"O vídeo existe, mas o OpenCV não conseguiu abri-lo:\n  {fonte}\n"
                "Causas comuns: codec incomum (converta para MP4/H.264) ou caminho com acentos "
                "(copie o vídeo para uma pasta simples, como C:\\videos).")
        raise SystemExit("Não consegui abrir a câmera. Verifique as permissões do "
                         "sistema e se outro programa não está usando a câmera.")
    if not args.video:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    fps_video = cap.get(cv2.CAP_PROP_FPS) or 30.0
    leitor = Leitor(cap, descartar=(not args.video) or args.tempo_real,
                    simular_relogio=bool(args.video and args.tempo_real), fps=fps_video)

    if detector.nome == "yolo":                          # aquece o YOLO (a primeira chamada é lenta)
        detector.detectar(np.zeros((540, PROC_WIDTH, 3), np.uint8))
    leitor.start()

    totais = {}                                          # vegetal -> [frescos, estragados, incertos]
    ignorados = [0]
    usar_mascara = not args.sem_mascara
    roi = tuple(float(v) for v in args.roi.split(",")) if args.roi else None
    estado_loop = {"frame_idx": 0, "rastreador": None}

    def ao_finalizar(t):
        fr, _, p_est = interpretar(t.probs_medias(), frutas, mat, estragada)
        if filtro and fr != filtro:
            ignorados[0] += 1
            return
        v = totais.setdefault(fr, [0, 0, 0])
        if p_est >= HIGH:
            v[1] += 1
        elif p_est <= LOW:
            v[0] += 1
        else:
            v[2] += 1

    def aplicar_resultados():
        rast = estado_loop["rastreador"]
        for ids, probs in clf.coletar():
            for tid, p in zip(ids, probs):
                t = rast.mapa.get(tid) if rast else None
                if t is not None:
                    t.add_probs(p, estado_loop["frame_idx"])

    rastreador, frame_idx = None, 0
    tempos, por_visiveis = [], {}
    t_det_med, fps, prev = 0.0, 0.0, time.perf_counter()
    janela = "Esteira de frutas"
    try:
        while True:
            if args.arquivo_parar and os.path.exists(args.arquivo_parar):
                print("Parada solicitada pelo aplicativo.")
                break
            frame_full = leitor.ler()
            if frame_full is None:
                break
            t_ini = time.perf_counter()
            escala = min(1.0, PROC_WIDTH / frame_full.shape[1])
            frame = frame_full if escala == 1.0 else cv2.resize(frame_full, None, fx=escala, fy=escala,
                                                                 interpolation=cv2.INTER_AREA)
            h, w = frame.shape[:2]
            if rastreador is None:
                rastreador = Rastreador(w, ao_finalizar)
                estado_loop["rastreador"] = rastreador

            t0 = time.perf_counter()
            caixas = detector.detectar(frame)
            t_det_med = 0.9 * t_det_med + 0.1 * (time.perf_counter() - t0) * 1000
            if roi:                                     # só vale o que está dentro da área da esteira
                caixas = [b for b in caixas
                          if roi[0] * w <= b[0] + b[2] / 2 <= roi[2] * w
                          and roi[1] * h <= b[1] + b[3] / 2 <= roi[3] * h]
            rastreador.atualizar(caixas)

            aplicar_resultados()
            cand = escolher_para_classificar(rastreador.itens, frame_idx, w, h)
            if cand:
                crops = [recortar_para_modelo(frame_full, t.caixa, escala, usar_mascara) for t in cand]
                if clf.enviar([t.id for t in cand], crops):
                    for t in cand:
                        t.pendente = True

            visiveis = [t for t in rastreador.itens if t.perdida == 0]
            if not args.sem_janela:
                for t in visiveis:                       # ---- desenho
                    x, y, bw, bh = t.caixa
                    pm = t.probs_medias()
                    if pm is None:
                        cor, texto = (170, 170, 170), f"#{t.id} ..."
                    else:
                        fr, conf_fr, p_est = interpretar(pm, frutas, mat, estragada)
                        estado, cor, conf = veredito(p_est)
                        nome = nome_pt(fr) + ("?" if conf_fr < 0.5 else "")
                        if filtro and fr != filtro:
                            cor = (120, 120, 120)
                        texto = f"#{t.id} {nome} | {estado} {conf * 100:.0f}%"
                    cv2.rectangle(frame, (x, y), (x + bw, y + bh), cor, 2)
                    (tw, th), _ = cv2.getTextSize(texto, FONT, 0.5, 1)
                    y0 = max(0, y - th - 8)
                    cv2.rectangle(frame, (x, y0), (x + tw + 6, y0 + th + 8), cor, -1)
                    cv2.putText(frame, texto, (x + 3, y0 + th + 2), FONT, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                if roi:
                    cv2.rectangle(frame, (int(roi[0] * w), int(roi[1] * h)), (int(roi[2] * w), int(roi[3] * h)),
                                  (255, 200, 0), 1)
                linhas = [f"{nome_pt(fr)}: {v[0]} frescos | {v[1]} estragados"
                          for fr, v in sorted(totais.items())]
                n_inc = sum(v[2] for v in totais.values())
                linhas.append(f"Incertos: {n_inc}" + (f" | Ignorados: {ignorados[0]}" if filtro else ""))
                painel = frame.copy()
                cv2.rectangle(painel, (0, 0), (380, 36 + 22 * len(linhas)), (0, 0, 0), -1)
                frame = cv2.addWeighted(painel, 0.6, frame, 0.4, 0)
                cv2.putText(frame, "CONTAGEM", (10, 22), FONT, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
                for i, tx in enumerate(linhas):
                    cv2.putText(frame, tx, (10, 46 + 22 * i), FONT, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
                info = (f"{fps:.0f} FPS | det {t_det_med:.0f} ms | rede {clf.t_medio:.0f} ms "
                        f"(fila {clf.fila()}) | {len(visiveis)} frutas | {detector.nome}")
                if leitor.descartar and args.video:
                    info += f" | descartados {leitor.descartados}"
                cv2.putText(frame, info, (10, h - 12), FONT, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.imshow(janela, frame)

            agora = time.perf_counter()
            fps = 0.9 * fps + 0.1 * (1 / max(agora - prev, 1e-6))
            prev = agora
            dt = (agora - t_ini) * 1000
            tempos.append(dt)
            faixa = "0-3" if len(visiveis) <= 3 else ("4-7" if len(visiveis) <= 7 else "8+")
            por_visiveis.setdefault(faixa, []).append(dt)
            frame_idx += 1
            estado_loop["frame_idx"] = frame_idx

            if not args.sem_janela:
                tecla = cv2.waitKey(1) & 0xFF
                if tecla in (ord("q"), 27):
                    break
                elif tecla == ord("r"):
                    totais.clear()
                    ignorados[0] = 0
                elif tecla == ord("o"):                   # marcar a área da esteira
                    base = frame_full if escala == 1.0 else cv2.resize(frame_full, None, fx=escala, fy=escala)
                    r = cv2.selectROI(janela, base, False)
                    if r[2] > 10 and r[3] > 10:
                        roi = (r[0] / w, r[1] / h, (r[0] + r[2]) / w, (r[1] + r[3]) / h)
                elif detector.nome == "cor":
                    if tecla == ord("b"):
                        detector.recalibrar = True
                    elif tecla == ord("m") and detector.mask is not None:
                        cv2.imshow("Mascara", detector.mask)
                    elif tecla in (ord("+"), ord("=")):
                        detector.limiar += 2
                    elif tecla in (ord("-"), ord("_")):
                        detector.limiar = max(4, detector.limiar - 2)
    finally:
        leitor.encerrar()
        cap.release()
        if not args.sem_janela:
            cv2.destroyAllWindows()
            for _ in range(5):
                cv2.waitKey(1)
        clf.esperar()
        if rastreador is not None:
            aplicar_resultados()
            rastreador.finalizar_todos()
        clf.encerrar()
        print("\nResumo da contagem:")
        for fr, v in sorted(totais.items()):
            gab = ler_gabarito(args.video, fr) if args.video else None
            print(resumo_texto(fr, v, gab))
        if not totais:
            print("  (nenhuma fruta contada)")
        if filtro:
            print(f"  Ignorados (outros vegetais): {ignorados[0]}")
        total = sum(v[0] + v[1] + v[2] for v in totais.values())
        print(f"  Total: {total} frutas")
        if args.fornecedor and totais:
            try:
                import sys
                sys.path.insert(0, BASE_DIR)
                import frutas_db
                lote = frutas_db.registrar_contagem_esteira(args.fornecedor, totais, referencia=args.referencia)
                forn = frutas_db.achar_fornecedor(args.fornecedor)
                print(f"  Contagem gravada no banco (lote #{lote}, fornecedor '{forn['nome'] if forn else args.fornecedor}'): "
                      f"{frutas_db.DB_PATH}")
            except Exception as e:           # nunca perde o resumo por causa do banco
                print(f"  ATENÇÃO: não consegui gravar no banco: {e}")
        elif args.fornecedor:
            print("  Nada para gravar no banco (nenhuma fruta contada).")
        if tempos:
            a = np.array(tempos)
            print(f"\nDesempenho: {frame_idx} frames | FPS médio {1000 / a.mean():.1f} | "
                  f"tempo por frame: média {a.mean():.1f} ms, p95 {np.percentile(a, 95):.1f} ms, máx {a.max():.1f} ms")
            for faixa in ("0-3", "4-7", "8+"):
                if faixa in por_visiveis:
                    v = np.array(por_visiveis[faixa])
                    print(f"  com {faixa} frutas visíveis: {v.mean():.1f} ms/frame ({len(v)} frames)")


if __name__ == "__main__":
    main()
