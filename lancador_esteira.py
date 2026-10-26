"""
Inicia, acompanha e encerra a esteira (esteira.py) a partir do app_frutas.py.

A esteira roda como um processo separado (abre a própria janela de vídeo do OpenCV). O encerramento
"normal" cria um arquivo-sinal que a esteira lê a cada quadro: ela para, grava a contagem no banco e sai.
Só o "forçar parada" mata o processo na hora (e, nesse caso, a contagem NÃO é gravada).
"""
import glob
import os
import re
import subprocess
import sys
import time

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

ESTEIRA = os.path.join(BASE_DIR, "esteira.py")
PASTA_LOGS = os.path.join(BASE_DIR, "logs_esteira")
PASTA_VIDEOS = os.path.join(BASE_DIR, "videos")
SINAL_PARADA = os.path.join(BASE_DIR, ".parar_esteira")
EXTENSOES_VIDEO = ("*.mp4", "*.avi", "*.mov", "*.mkv", "*.wmv")

# Estado compartilhado entre as execuções da página (o módulo fica carregado enquanto o servidor roda)
_estado = {"proc": None, "log": None, "log_fh": None, "info": {}, "inicio": 0.0, "pedido_parada": 0.0}


def arquivos_faltando():
    """Arquivos que a esteira precisa e ainda não existem (modelo treinado, classes)."""
    precisa = ["frutas_multiclasse.keras", "classes_frutas.json"]
    return [n for n in precisa if not os.path.exists(os.path.join(BASE_DIR, n))]


def videos_disponiveis():
    achados = []
    for pasta in (BASE_DIR, PASTA_VIDEOS):
        for ext in EXTENSOES_VIDEO:
            achados += glob.glob(os.path.join(pasta, ext))
    return sorted(set(achados), key=lambda p: os.path.basename(p).lower())


def salvar_video_enviado(nome, conteudo):
    """Guarda um vídeo enviado pelo navegador na pasta videos/ e devolve o caminho."""
    os.makedirs(PASTA_VIDEOS, exist_ok=True)
    nome = re.sub(r"[^\w.\- ]", "_", os.path.basename(nome))
    destino = os.path.join(PASTA_VIDEOS, nome)
    with open(destino, "wb") as f:
        f.write(conteudo)
    return destino


def em_execucao():
    p = _estado["proc"]
    if p is None:
        return False
    if p.poll() is None:
        return True
    _finalizar()
    return False


def _finalizar():
    fh = _estado.get("log_fh")
    if fh and not fh.closed:
        fh.close()
    _estado["log_fh"] = None
    if os.path.exists(SINAL_PARADA):
        try:
            os.remove(SINAL_PARADA)
        except OSError:
            pass


def iniciar(fornecedor_id, origem, video=None, camera=0, referencia="", tempo_real=False):
    """origem = 'video' ou 'camera'. Devolve o caminho do log. Levanta ValueError se não puder iniciar."""
    if em_execucao():
        raise ValueError("A esteira já está em execução.")
    faltam = arquivos_faltando()
    if faltam:
        raise ValueError("Faltam arquivos na pasta do programa: " + ", ".join(faltam) +
                         ". Rode o treino_multiclasse.py antes.")
    if not os.path.exists(ESTEIRA):
        raise ValueError(f"esteira.py não encontrado em {BASE_DIR}.")
    cmd = [sys.executable, "-u", ESTEIRA, "--fornecedor", str(int(fornecedor_id))]
    if origem == "video":
        if not video or not os.path.isfile(video):
            raise ValueError("Escolha um vídeo que exista.")
        cmd += ["--video", video]
        if tempo_real:
            cmd.append("--tempo-real")
    elif origem == "camera":
        cmd += ["--cam", str(int(camera))]
    else:
        raise ValueError("Origem inválida.")
    if referencia.strip():
        cmd += ["--referencia", referencia.strip()]
    if os.path.exists(SINAL_PARADA):
        os.remove(SINAL_PARADA)
    cmd += ["--arquivo-parar", SINAL_PARADA]

    os.makedirs(PASTA_LOGS, exist_ok=True)
    log = os.path.join(PASTA_LOGS, time.strftime("esteira_%Y%m%d_%H%M%S.log"))
    fh = open(log, "wb")
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    extra = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    _estado["proc"] = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=fh, stderr=subprocess.STDOUT, env=env, **extra)
    _estado.update(log=log, log_fh=fh, inicio=time.time(), pedido_parada=0.0,
                   info={"origem": origem, "video": video, "camera": camera, "fornecedor_id": int(fornecedor_id),
                         "referencia": referencia})
    return log


def pedir_parada():
    """Encerramento normal: a esteira para, grava a contagem e sai."""
    if em_execucao():
        with open(SINAL_PARADA, "w") as f:
            f.write("parar")
        _estado["pedido_parada"] = time.time()


def forcar_parada():
    """Mata o processo na hora. A contagem em andamento NÃO é gravada."""
    p = _estado["proc"]
    if p is not None and p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
    _finalizar()


def segundos_desde_pedido():
    t = _estado["pedido_parada"]
    return time.time() - t if t else 0.0


def segundos_rodando():
    return time.time() - _estado["inicio"] if _estado["inicio"] else 0.0


def ler_log(max_linhas=60):
    caminho = _estado.get("log")
    if not caminho or not os.path.exists(caminho):
        return ""
    with open(caminho, "rb") as f:
        texto = f.read().decode("utf-8", errors="replace")
    texto = texto.replace("\r", "\n")
    linhas = [l for l in texto.split("\n") if l.strip()]
    return "\n".join(linhas[-max_linhas:])


def resultado():
    """Depois que a esteira termina: {'codigo', 'lote', 'resumo', 'erro_banco'} (ou None se nunca rodou)."""
    p = _estado["proc"]
    if p is None or p.poll() is None:
        return None
    texto = ler_log(10_000)
    m = re.search(r"lote #(\d+)", texto)
    resumo = ""
    i = texto.find("Resumo da contagem:")
    if i >= 0:
        resumo = texto[i:]
        j = resumo.find("Desempenho:")
        if j >= 0:
            resumo = resumo[:j]
    erro = ""
    for linha in texto.split("\n"):
        if "não consegui gravar no banco" in linha:
            erro = linha.strip()
    return {"codigo": p.returncode, "lote": int(m.group(1)) if m else None, "resumo": resumo.strip(), "erro_banco": erro}
