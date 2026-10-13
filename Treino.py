# -*- coding: utf-8 -*-
"""
Created on Fri Oct  9 13:46:48 2026

@author: ltvia
"""

"""
Treina um classificador binário (fresca x estragada) com transfer learning
(MobileNetV2) usando o dataset ulnnproject/food-freshness-dataset.

Requer: tensorflow, keras>=3, kagglehub e PyTorch com CUDA (para usar a GPU).
Uso (terminal):  python train.py
Uso (Spyder):    abra o arquivo e pressione F5

Saídas:
    fruta_frescor.keras   -> modelo treinado
"""
import os
import random

# No Windows, caminhos com mais de 260 caracteres falham ao extrair este dataset
# (os nomes dos arquivos são muito longos). Usamos uma pasta de cache curta.
# Precisa ser definido ANTES de importar o kagglehub.
if os.name == "nt":
    os.environ.setdefault("KAGGLEHUB_CACHE", "C:\\kh")

# GPU no Windows: o TensorFlow nativo só usa CPU, então usamos o Keras 3 com backend
# PyTorch (que usa a GPU NVIDIA). Precisa ser definido ANTES de importar o keras.
os.environ["KERAS_BACKEND"] = "torch"
import torch

import kagglehub
import tensorflow as tf          # usado só para carregar/preparar as imagens (tf.data)
try:
    tf.config.set_visible_devices([], "GPU")   # o TF não disputa a GPU com o PyTorch
except RuntimeError:
    pass
import keras
from keras import layers
import torch

if int(keras.__version__.split(".")[0]) < 3:
    raise SystemExit("Keras 3 é necessário. Atualize com: pip install --upgrade tensorflow keras")
if keras.config.backend() != "torch":
    raise SystemExit(f"O Keras está usando o backend '{keras.config.backend()}'. "
                     "Reinicie o kernel do Spyder (Consoles > Restart kernel) e rode de novo.")
if torch.cuda.is_available():
    print(f"GPU detectada: {torch.cuda.get_device_name(0)}  (PyTorch {torch.__version__})")
else:
    print("ATENÇÃO: GPU NÃO detectada, o treino vai rodar na CPU (bem mais lento).\n"
          "Instale o PyTorch com CUDA (veja as instruções) e atualize o driver da NVIDIA.")

IMG_SIZE = 224
BATCH = 32
EPOCHS_HEAD = 6      # treino só da "cabeça" do modelo
EPOCHS_FINE = 6      # fine-tuning das últimas camadas
SEED = 42
VAL_SPLIT = 0.2
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:               # ao rodar célula/seleção no Spyder, __file__ não existe
    BASE_DIR = os.getcwd()
MODEL_PATH = os.path.join(BASE_DIR, "fruta_frescor.keras")   # salvo ao lado do script

EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
# A checagem de "estragada" vem primeiro para evitar ambiguidades.
ROTTEN_KEYS = ("rotten", "spoil", "stale", "bad", "podre", "estragad")
FRESH_KEYS = ("fresh", "good", "fresco", "fresca")

# ---------------------------------------------------------------- dataset
path = kagglehub.dataset_download("ulnnproject/food-freshness-dataset")
print("Path to dataset files:", path)


def label_from_path(rel_path: str):
    """0 = fresca, 1 = estragada, None = não identificada.
    Usa só o caminho RELATIVO (o nome do dataset já contém 'fresh')."""
    p = rel_path.lower()
    if any(k in p for k in ROTTEN_KEYS):
        return 1
    if any(k in p for k in FRESH_KEYS):
        return 0
    return None


files, labels, pastas = [], [], {}
for root, _, names in os.walk(path):
    for n in names:
        if not n.lower().endswith(EXTS):
            continue
        full = os.path.join(root, n)
        rel = os.path.relpath(full, path)
        y = label_from_path(rel)
        if y is None:
            continue
        files.append(full)
        labels.append(y)
        pastas[os.path.dirname(rel)] = y

print(f"\nImagens: {len(files)} | frescas: {labels.count(0)} | estragadas: {labels.count(1)}")
print("Pastas -> classe (0=fresca, 1=estragada):")
for k, v in sorted(pastas.items()):
    print(f"  {v}  {k}")
if labels.count(0) == 0 or labels.count(1) == 0:
    raise SystemExit("Não encontrei as duas classes. Ajuste ROTTEN_KEYS/FRESH_KEYS "
                     "conforme os nomes das pastas impressos acima.")

# split embaralhado e estratificado
random.seed(SEED)
train_f, train_y, val_f, val_y = [], [], [], []
for cls in (0, 1):
    idx = [i for i, y in enumerate(labels) if y == cls]
    random.shuffle(idx)
    cut = int(len(idx) * (1 - VAL_SPLIT))
    for i in idx[:cut]:
        train_f.append(files[i]); train_y.append(cls)
    for i in idx[cut:]:
        val_f.append(files[i]); val_y.append(cls)


def load(path_, y):
    img = tf.io.read_file(path_)
    img = tf.io.decode_image(img, channels=3, expand_animations=False)
    img = tf.image.resize(img, (IMG_SIZE, IMG_SIZE))
    img.set_shape((IMG_SIZE, IMG_SIZE, 3))
    return img, tf.cast(y, tf.float32)


def make_ds(f, y, training):
    ds = tf.data.Dataset.from_tensor_slices((f, y))
    if training:
        ds = ds.shuffle(len(f), seed=SEED)
    ds = ds.map(load, num_parallel_calls=tf.data.AUTOTUNE).ignore_errors()  # ignora imagens corrompidas
    return ds.batch(BATCH).prefetch(tf.data.AUTOTUNE)


train_ds = make_ds(train_f, train_y, True)
val_ds = make_ds(val_f, val_y, False)

# pesos de classe (caso o dataset seja desbalanceado)
n0, n1 = train_y.count(0), train_y.count(1)
total = n0 + n1
class_weight = {0: total / (2 * n0), 1: total / (2 * n1)}

# ----------------------------------------------------------------- modelo
augment = keras.Sequential([
    layers.RandomFlip("horizontal"),
    layers.RandomRotation(0.1),
    layers.RandomZoom(0.15),
    layers.RandomContrast(0.2),
    layers.RandomBrightness(0.2, value_range=(0, 255)),
], name="augmentation")

base = keras.applications.MobileNetV2(
    input_shape=(IMG_SIZE, IMG_SIZE, 3), include_top=False, weights="imagenet")
base.trainable = False

inputs = keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3))          # RGB 0-255
x = augment(inputs)
x = keras.applications.mobilenet_v2.preprocess_input(x)       # normalização dentro do modelo
x = base(x, training=False)
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.3)(x)
outputs = layers.Dense(1, activation="sigmoid")(x)            # P(estragada)
model = keras.Model(inputs, outputs)

callbacks = [
    keras.callbacks.ModelCheckpoint(MODEL_PATH, monitor="val_accuracy",
                                    save_best_only=True, verbose=1),
    keras.callbacks.EarlyStopping(monitor="val_loss", patience=3,
                                  restore_best_weights=True),
]
metrics = ["accuracy", keras.metrics.AUC(name="auc")]

# fase 1: só a cabeça
model.compile(optimizer=keras.optimizers.Adam(1e-3),
              loss="binary_crossentropy", metrics=metrics)
model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS_HEAD,
          class_weight=class_weight, callbacks=callbacks)

# fase 2: fine-tuning das últimas 30 camadas
base.trainable = True
for layer in base.layers[:-30]:
    layer.trainable = False
model.compile(optimizer=keras.optimizers.Adam(1e-5),
              loss="binary_crossentropy", metrics=metrics)
model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS_FINE,
          class_weight=class_weight, callbacks=callbacks)

print("\nAvaliação final (validação):")
model.evaluate(val_ds)
model.save(MODEL_PATH)
if os.path.exists(MODEL_PATH):
    print(f"\nOK! Modelo salvo em: {os.path.abspath(MODEL_PATH)}")
else:
    print(f"\nATENÇÃO: o arquivo não foi encontrado após salvar: {MODEL_PATH}")