# -*- coding: utf-8 -*-
"""
Created on Fri Oct  9 20:40:57 2026

@author: ltvia
"""

"""
Treina um classificador MULTICLASSE: identifica a fruta E se está fresca ou estragada.
Cada pasta do dataset vira uma classe (ex.: FreshOrange, RottenApple, ...).

Requer: tensorflow, keras>=3, kagglehub e PyTorch com CUDA (para usar a GPU).
Uso (Spyder): abra o arquivo e pressione F5.  Terminal: python treino_multiclasse.py

Saídas (na pasta do script):
    frutas_multiclasse.keras   -> modelo treinado
    classes_frutas.json        -> lista de classes (fruta + estado), usada pelo esteira.py
"""
import hashlib
import json
import os
import random
import re
from collections import Counter, defaultdict
 
# No Windows, caminhos com mais de 260 caracteres falham ao extrair este dataset.
# Usamos uma pasta de cache curta. Definir ANTES de importar o kagglehub.
if os.name == "nt":
    os.environ.setdefault("KAGGLEHUB_CACHE", "C:\\kh")
 
# GPU no Windows: Keras 3 com backend PyTorch. Definir ANTES de importar o keras.
os.environ["KERAS_BACKEND"] = "torch"
 
import numpy as np
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
    print("ATENÇÃO: GPU NÃO detectada, o treino vai rodar na CPU (bem mais lento).")
 
# ------------------------------------------------------------ parâmetros
IMG_SIZE = 224
BATCH = 32
EPOCHS_HEAD = 8          # treino só da "cabeça" do modelo
EPOCHS_FINE = 15          # fine-tuning das últimas camadas
SEED = 42
VAL_SPLIT = 0.2
MAX_POR_CLASSE = None    # ex.: 3000 para treinar mais rápido (None = usa todas as imagens)
MIN_IMGS = 20            # classes com menos imagens que isso são descartadas
REMOVER_DUPLICATAS = True   # descarta arquivos idênticos que aparecem em mais de um dataset
 
# Datasets baixados pelo kagglehub (cada um fica na sua própria pasta de cache).
FONTES_KAGGLE = [
    "ulnnproject/food-freshness-dataset",
    "muhammad0subhan/fruit-and-vegetable-disease-healthy-vs-rotten",
]
# Pastas que você baixou manualmente (Mendeley, Roboflow, suas próprias fotos...).
# Podem ficar em qualquer lugar; não precisa misturar com as outras.
# Ex.: [r"C:\datasets\FruitNet", r"C:\datasets\minhas_fotos"]
PASTAS_LOCAIS = []
 
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:               # ao rodar célula/seleção no Spyder, __file__ não existe
    BASE_DIR = os.getcwd()
MODEL_PATH = os.path.join(BASE_DIR, "frutas_multiclasse.keras")
CLASSES_PATH = os.path.join(BASE_DIR, "classes_frutas.json")
 
EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
 
# >>> auxiliares (nomenclatura) ------------------------------------------------
# A checagem de "estragada" vem primeiro para evitar ambiguidades (ex.: "unhealthy").
ROTTEN_KEYS = ("rotten", "spoiled", "spoil", "stale", "unhealthy", "diseased", "bad",
               "podre", "estragad")
FRESH_KEYS = ("fresh", "healthy", "good", "fresco", "fresca", "saudavel")
STRIP_RE = re.compile(r"(rotten|spoiled|spoil|stale|unhealthy|diseased|healthy|fresh|good|bad|"
                      r"podres?|estragad[oa]s?|frescos?|frescas?|saudavel|saudaveis)")
# pastas "genéricas" que não dizem qual é a fruta
PASTAS_GENERICAS = {"train", "training", "test", "testing", "valid", "validation", "val",
                    "dataset", "data", "images", "image", "imgs", "photos", "fotos"}
 
# Nomes alternativos / erros de grafia -> nome padrão (chave: minúsculas, sem símbolos).
ALIAS_FRUTAS = {
    "capciscum": "Bellpepper", "capsicum": "Bellpepper", "bellpepper": "Bellpepper",
    "bellpeppers": "Bellpepper", "pepper": "Bellpepper", "peppers": "Bellpepper",
    "okara": "Okra", "ladyfinger": "Okra", "ladysfinger": "Okra",
    "bittergroud": "Bittergourd", "bittergourd": "Bittergourd", "bittermelon": "Bittergourd",
    "apples": "Apple", "bananas": "Banana", "oranges": "Orange", "mangoes": "Mango",
    "mangos": "Mango", "grapes": "Grape", "strawberries": "Strawberry", "tomatoes": "Tomato",
    "potatoes": "Potato", "carrots": "Carrot", "cucumbers": "Cucumber",
    "pomegranates": "Pomegranate", "guavas": "Guava", "limes": "Lime", "jujubes": "Jujube",
}
 
 
def estado_do_caminho(rel_path: str):
    """0 = fresca, 1 = estragada, None = não identificada (usa só o caminho RELATIVO)."""
    p = rel_path.lower()
    if any(k in p for k in ROTTEN_KEYS):
        return 1
    if any(k in p for k in FRESH_KEYS):
        return 0
    return None
 
 
def nome_limpo(componente: str):
    """'Apple__Healthy' -> 'apple' | 'FreshOrange' -> 'orange' | 'Fresh' -> ''."""
    nome = STRIP_RE.sub(" ", componente.lower())
    return re.sub(r"[^a-z0-9]+", "", nome)
 
 
def fruta_do_caminho(rel_path: str):
    """Procura o nome da fruta subindo da pasta mais interna para a mais externa
    (assim 'Fresh/Apple', 'Apple/Fresh', 'FreshApple' e 'Apple__Healthy' dão 'Apple')."""
    partes = os.path.normpath(os.path.dirname(rel_path)).split(os.sep)
    for comp in reversed(partes):
        token = nome_limpo(comp)
        if token and token not in PASTAS_GENERICAS:
            return ALIAS_FRUTAS.get(token, token.title())
    return "Fruta"
 
 
def grupo_da_foto(caminho: str):
    """Identifica a foto ORIGINAL, para que cópias aumentadas (Roboflow '_jpg.rf.<hash>',
    prefixos 'rotated_by_', 'flipped_'...) fiquem todas do mesmo lado do split."""
    stem = os.path.splitext(os.path.basename(caminho))[0]
    stem = re.split(r"_(?:jpg|jpeg|png|bmp)\.rf\.", stem, flags=re.I)[0]
    return re.sub(r"^(?:rotated_by_\d+_|flipped_|aug(?:mented)?_)+", "", stem, flags=re.I)
 
 
def dividir_por_grupo(arquivos):
    grupos = {}
    for a in arquivos:
        grupos.setdefault(grupo_da_foto(a), []).append(a)
    chaves = list(grupos)
    random.shuffle(chaves)
    alvo = len(arquivos) * (1 - VAL_SPLIT)
    treino, val, n = [], [], 0
    for k in chaves:
        if n < alvo:
            treino += grupos[k]
            n += len(grupos[k])
        else:
            val += grupos[k]
    return treino, val
 
 
def hash_rapido(caminho: str):
    try:
        with open(caminho, "rb") as f:
            return os.path.getsize(caminho), hashlib.md5(f.read(65536)).hexdigest()
    except OSError:
        return caminho
# <<< fim auxiliares -----------------------------------------------------------
 
# ---------------------------------------------------------------- datasets
# Cada dataset fica na sua própria pasta; aqui só juntamos as listas de arquivos.
raizes = []      # (nome, pasta)
for slug in FONTES_KAGGLE:
    try:
        caminho = kagglehub.dataset_download(slug)
        print(f"Dataset '{slug}':", caminho)
        raizes.append((slug, caminho))
    except Exception as e:                       # um dataset com problema não derruba os outros
        print(f"AVISO: não consegui baixar '{slug}': {e}")
for pasta in PASTAS_LOCAIS:
    if os.path.isdir(pasta):
        raizes.append((pasta, pasta))
    else:
        print(f"AVISO: pasta local não encontrada: {pasta}")
if not raizes:
    raise SystemExit("Nenhuma fonte de dados disponível.")
 
por_classe = defaultdict(list)             # (fruta, estado) -> arquivos
por_fonte = defaultdict(Counter)           # (fruta, estado) -> {nº da fonte: quantidade}
vistos, n_dup = set(), 0
for i, (rotulo, raiz) in enumerate(raizes, start=1):
    achadas = 0
    for root, _, names in os.walk(raiz):
        for n in names:
            if not n.lower().endswith(EXTS):
                continue
            full = os.path.join(root, n)
            rel = os.path.relpath(full, raiz)
            estado = estado_do_caminho(rel)
            if estado is None:
                continue
            if REMOVER_DUPLICATAS:
                h = hash_rapido(full)
                if h in vistos:
                    n_dup += 1
                    continue
                vistos.add(h)
            chave = (fruta_do_caminho(rel), estado)
            por_classe[chave].append(full)
            por_fonte[chave][i] += 1
            achadas += 1
    print(f"  fonte [{i}] {rotulo}: {achadas} imagens aproveitadas")
if n_dup:
    print(f"  {n_dup} arquivos duplicados descartados")
 
random.seed(SEED)
classes = []
for (fruta, estado), arquivos in sorted(por_classe.items()):
    if len(arquivos) < MIN_IMGS:
        print(f"Descartando classe com poucas imagens: {fruta}/{estado} ({len(arquivos)})")
        continue
    nome = ("Rotten" if estado else "Fresh") + fruta
    classes.append({"name": nome, "fruit": fruta, "rotten": bool(estado), "files": arquivos,
                    "src": dict(por_fonte[(fruta, estado)])})
 
if len(classes) < 2:
    raise SystemExit("Menos de 2 classes encontradas. Confira os nomes das pastas dos datasets.")
 
print(f"\n{len(classes)} classes (fontes entre colchetes):")
for c in classes:
    fontes = ", ".join(f"[{k}]={v}" for k, v in sorted(c["src"].items()))
    print(f"  {c['name']:<26} fruta={c['fruit']:<12} estragada={c['rotten']!s:<5} "
          f"imagens={len(c['files']):<6} {fontes}")
frutas_sem_par = [f for f in {c["fruit"] for c in classes}
                  if len({c["rotten"] for c in classes if c["fruit"] == f}) < 2]
if frutas_sem_par:
    print("\nATENÇÃO: estas frutas só têm UM estado (fresca ou estragada), o que ensina o "
          "modelo a associar a fruta ao estado:", ", ".join(sorted(frutas_sem_par)))
 
# ------------------------------- split estratificado (sem separar fotos aumentadas)
train_f, train_y, val_f, val_y = [], [], [], []
for idx, c in enumerate(classes):
    arq = c["files"][:]
    random.shuffle(arq)
    if MAX_POR_CLASSE:
        arq = arq[:MAX_POR_CLASSE]
    tr, va = dividir_por_grupo(arq)
    train_f += tr; train_y += [idx] * len(tr)
    val_f += va;   val_y += [idx] * len(va)
 
# salva a lista de classes (sem os caminhos) para o script de tempo real
with open(CLASSES_PATH, "w", encoding="utf-8") as f:
    json.dump({"classes": [{k: c[k] for k in ("name", "fruit", "rotten")} for c in classes]},
              f, ensure_ascii=False, indent=2)
print("Lista de classes salva em", CLASSES_PATH)
 
 
def load(path_, y):
    img = tf.io.read_file(path_)
    img = tf.io.decode_image(img, channels=3, expand_animations=False)
    img = tf.image.resize(img, (IMG_SIZE, IMG_SIZE))
    img.set_shape((IMG_SIZE, IMG_SIZE, 3))
    return img, tf.cast(y, tf.int32)
 
 
def make_ds(f, y, training):
    ds = tf.data.Dataset.from_tensor_slices((f, y))
    if training:
        ds = ds.shuffle(len(f), seed=SEED)
    ds = ds.map(load, num_parallel_calls=tf.data.AUTOTUNE).ignore_errors()  # ignora imagens corrompidas
    return ds.batch(BATCH).prefetch(tf.data.AUTOTUNE)
 
 
train_ds = make_ds(train_f, train_y, True)
val_ds = make_ds(val_f, val_y, False)
 
# pesos de classe (caso o dataset seja desbalanceado)
contagem = np.bincount(train_y, minlength=len(classes))
class_weight = {i: float(len(train_y) / (len(classes) * max(n, 1))) for i, n in enumerate(contagem)}
 
# ----------------------------------------------------------------- modelo
# Na esteira as frutas chegam em qualquer posição/orientação -> aumento de dados mais forte.
augment = keras.Sequential([
    layers.RandomFlip("horizontal_and_vertical"),
    layers.RandomRotation(0.25),
    layers.RandomZoom(0.2),
    layers.RandomContrast(0.25),
    layers.RandomBrightness(0.25, value_range=(0, 255)),
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
outputs = layers.Dense(len(classes), activation="softmax")(x)
model = keras.Model(inputs, outputs)
 
callbacks = [
    keras.callbacks.ModelCheckpoint(MODEL_PATH, monitor="val_accuracy",
                                    save_best_only=True, verbose=1),
    keras.callbacks.EarlyStopping(monitor="val_loss", patience=3,
                                  restore_best_weights=True),
]
 
# fase 1: só a cabeça
model.compile(optimizer=keras.optimizers.Adam(1e-3),
              loss="sparse_categorical_crossentropy", metrics=["accuracy"])
model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS_HEAD,
          class_weight=class_weight, callbacks=callbacks)
 
# fase 2: fine-tuning das últimas 30 camadas
base.trainable = True
for layer in base.layers[:-30]:
    layer.trainable = False
model.compile(optimizer=keras.optimizers.Adam(1e-5),
              loss="sparse_categorical_crossentropy", metrics=["accuracy"])
model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS_FINE,
          class_weight=class_weight, callbacks=callbacks)
 
model.save(MODEL_PATH)
if os.path.exists(MODEL_PATH):
    print(f"\nOK! Modelo salvo em: {os.path.abspath(MODEL_PATH)}")
else:
    print(f"\nATENÇÃO: o arquivo não foi encontrado após salvar: {MODEL_PATH}")
 
# ------------------------------------------------- avaliação separada
# acurácia da classe completa, só da fruta e só do estado (fresca/estragada)
y_true = np.concatenate([yb.numpy() for _, yb in val_ds])
y_pred = model.predict(val_ds, verbose=0).argmax(axis=1)
frutas = sorted({c["fruit"] for c in classes})
fruta_id = np.array([frutas.index(c["fruit"]) for c in classes])
estragada = np.array([c["rotten"] for c in classes])
print("\nAvaliação na validação:")
print(f"  classe completa : {(y_true == y_pred).mean() * 100:.1f}%")
print(f"  só a fruta      : {(fruta_id[y_true] == fruta_id[y_pred]).mean() * 100:.1f}%")
print(f"  fresca/estragada: {(estragada[y_true] == estragada[y_pred]).mean() * 100:.1f}%")