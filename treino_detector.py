r"""
Treina o DETECTOR de frutas (YOLO, uma classe: "fruta") com o dataset gerado por
gerar_dataset_deteccao.py. É ele que separa frutas encostadas/sobrepostas.

Uso (Anaconda Prompt, na pasta dos scripts):
    python -m pip install ultralytics
    python gerar_dataset_deteccao.py
    python treino_detector.py
    python treino_detector.py --epocas 60 --modelo yolo11s.pt    # mais preciso, mais lento

Saída: fruta_detector.pt (o esteira.py usa esse arquivo automaticamente, se existir).
"""
import argparse
import os
import shutil

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:               # ao rodar célula/seleção no Spyder, __file__ não existe
    BASE_DIR = os.getcwd()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", default=os.path.join(BASE_DIR, "dataset_detector", "data.yaml"))
    ap.add_argument("--modelo", default="yolo11n.pt", help="ponto de partida (n = rápido, s = mais preciso)")
    ap.add_argument("--epocas", type=int, default=40)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--saida", default=os.path.join(BASE_DIR, "fruta_detector.pt"))
    args, _ = ap.parse_known_args()

    if not os.path.exists(args.dados):
        raise SystemExit(f"Dataset não encontrado: {args.dados}\nRode antes: python gerar_dataset_deteccao.py")
    base = os.path.dirname(os.path.abspath(args.dados))
    n_train = len([n for n in os.listdir(os.path.join(base, "images", "train"))]) \
        if os.path.isdir(os.path.join(base, "images", "train")) else 0
    if n_train == 0:
        raise SystemExit(
            f"Não há imagens de treino em:\n  {os.path.join(base, 'images', 'train')}\n"
            "Rode antes (na mesma pasta dos scripts):  python gerar_dataset_deteccao.py\n"
            "Se já rodou, confira se ele terminou com 'Pronto! ... imagens de treino'. "
            "Para usar outro local, informe --dados CAMINHO\\data.yaml")
    print(f"Dataset: {n_train} imagens de treino em {base}")
    try:
        from ultralytics import YOLO
        import torch
    except ImportError:
        raise SystemExit("Instale o ultralytics:  python -m pip install ultralytics")

    device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Treinando em: {'GPU ' + torch.cuda.get_device_name(0) if device == 0 else 'CPU (lento)'}")
    modelo = YOLO(args.modelo)
    modelo.train(
        data=args.dados, epochs=args.epocas, imgsz=args.imgsz, batch=args.batch, device=device,
        project=os.path.join(BASE_DIR, "runs_detector"), name="fruta", exist_ok=True,
        patience=10, workers=2,
        degrees=15, flipud=0.5, fliplr=0.5, mosaic=1.0, hsv_h=0.01, hsv_s=0.5, hsv_v=0.35,
    )
    melhor = os.path.join(BASE_DIR, "runs_detector", "fruta", "weights", "best.pt")
    if not os.path.exists(melhor):
        raise SystemExit("O treino não gerou best.pt; veja as mensagens acima.")
    shutil.copy(melhor, args.saida)
    print(f"\nOK! Detector salvo em: {args.saida}")
    print('Agora rode:  python esteira.py --video "seu_video.mp4"')


if __name__ == "__main__":
    main()
