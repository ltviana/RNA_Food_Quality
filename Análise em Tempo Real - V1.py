# -*- coding: utf-8 -*-
"""
Created on Fri Oct  9 13:50:29 2026

@author: ltvia
"""

"""
Reconhecimento em tempo real (webcam) de fruta fresca x estragada.

Compatível com Spyder (F5) e com terminal (python realtime.py).
Posicione a fruta dentro do quadrado central. Teclas: 'q' ou ESC para sair.

No Spyder, para a janela da câmera funcionar bem, rode em um terminal externo:
Run > Configuration per file... > "Execute in an external system terminal".
"""
import argparse
import os
import time
from collections import deque

import cv2
import numpy as np

# Usa o mesmo backend do treino (PyTorch, que roda na GPU). Definir ANTES de importar o keras.
os.environ.setdefault("KERAS_BACKEND", "torch")
import keras

IMG_SIZE = 224
# caminho do modelo relativo à pasta deste script (funciona em qualquer diretório de trabalho)
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:               # ao rodar célula/seleção no Spyder, __file__ não existe
    BASE_DIR = os.getcwd()
MODEL_PATH = os.path.join(BASE_DIR, "fruta_frescor.keras")
SMOOTH = 10              # nº de frames usados na média (reduz tremulação)
LOW, HIGH = 0.35, 0.65   # faixa de incerteza


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--model", default=MODEL_PATH)
    args, _ = ap.parse_known_args()   # ignora argumentos extras injetados pelo Spyder/IPython

    if not os.path.exists(args.model):
        raise SystemExit(
            f"Modelo não encontrado em:\n  {args.model}\n"
            "Rode o train.py até o fim (ele deve imprimir 'OK! Modelo salvo em: ...') "
            "ou passe o caminho com --model.")
    model = keras.models.load_model(args.model)
    print("Backend do Keras:", keras.config.backend())

    # Ao abrir a câmera, o sistema operacional solicita a permissão de acesso.
    cap = cv2.VideoCapture(args.cam)
    if not cap.isOpened():
        raise SystemExit("Não consegui acessar a webcam. Verifique as permissões do "
                         "sistema e se outro programa não está usando a câmera.")

    hist = deque(maxlen=SMOOTH)
    prev = time.time()
    fps = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)  # efeito espelho
            h, w = frame.shape[:2]

            # região central quadrada (ROI) onde a fruta deve ficar
            side = int(min(h, w) * 0.6)
            x0, y0 = (w - side) // 2, (h - side) // 2
            roi = frame[y0:y0 + side, x0:x0 + side]

            rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
            rgb = cv2.resize(rgb, (IMG_SIZE, IMG_SIZE))
            x = np.expand_dims(rgb.astype("float32"), 0)   # 0-255; normalização está no modelo

            p_rotten = float(keras.ops.convert_to_numpy(model(x, training=False))[0][0])
            hist.append(p_rotten)
            p = sum(hist) / len(hist)

            if p >= HIGH:
                text, color, conf = "ESTRAGADA", (0, 0, 255), p
            elif p <= LOW:
                text, color, conf = "FRESCA", (0, 200, 0), 1 - p
            else:
                text, color, conf = "INCERTO", (0, 200, 255), max(p, 1 - p)

            cv2.rectangle(frame, (x0, y0), (x0 + side, y0 + side), color, 3)
            cv2.rectangle(frame, (0, 0), (w, 50), (0, 0, 0), -1)
            cv2.putText(frame, f"{text}  {conf * 100:.0f}%", (10, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2, cv2.LINE_AA)

            now = time.time()
            fps = 0.9 * fps + 0.1 * (1 / max(now - prev, 1e-6))
            prev = now
            cv2.putText(frame, f"{fps:.0f} FPS", (w - 110, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

            cv2.imshow("Frescor das frutas", frame)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break
    finally:
        # sempre libera a câmera e fecha a janela, mesmo se der erro
        # (importante no Spyder, onde o kernel continua vivo após o script)
        cap.release()
        cv2.destroyAllWindows()
        for _ in range(5):
            cv2.waitKey(1)


if __name__ == "__main__":
    main()