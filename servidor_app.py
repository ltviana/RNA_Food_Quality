"""
Servidor do aplicativo de Controle de Qualidade de Frutas.

A interface é feita em HTML/CSS/JavaScript (pasta web/). Este servidor, só com a biblioteca padrão
do Python, entrega essas páginas e uma API JSON que usa o mesmo banco (frutas_db.py) e o mesmo
lançador da esteira (lancador_esteira.py).

Como abrir (Anaconda Prompt, na pasta dos scripts):
    python servidor_app.py                 # abre o navegador em http://localhost:8600
    python servidor_app.py --porta 9000    # outra porta
    python servidor_app.py --rede          # permite acesso de outros computadores da rede

Ou dê dois cliques em iniciar_app.bat (abre numa janela própria e não prende o prompt).
"""
import argparse
import json
import mimetypes
import os
import secrets
import socket
import sys
import threading
import time
import traceback
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()
sys.path.insert(0, BASE_DIR)

import frutas_db as db                 # noqa: E402
import lancador_esteira as lanc        # noqa: E402

PASTA_WEB = os.path.join(BASE_DIR, "web")
DURACAO_SESSAO = 12 * 3600             # segundos
MAX_JSON = 2 * 1024 * 1024             # 2 MB
MAX_VIDEO = 4 * 1024 ** 3              # 4 GB

_sessoes = {}                          # token -> {"login": ..., "expira": ...}
_tentativas = {}                       # login -> (falhas, bloqueado_ate)
_trava = threading.Lock()


class ErroHTTP(Exception):
    def __init__(self, status, msg):
        super().__init__(msg)
        self.status, self.msg = status, msg


def exigir(usuario, *perfis):
    if usuario is None:
        raise ErroHTTP(401, "Faça login para continuar.")
    if perfis and usuario["perfil"] not in perfis:
        raise ErroHTTP(403, "Seu perfil não tem permissão para esta ação.")


def usuario_atual(login):
    with db.conexao() as con:
        r = con.execute("SELECT id, login, nome, perfil FROM usuarios WHERE login=? AND ativo=1", (login,)).fetchone()
    return dict(r) if r else None


def lista_ids(texto):
    return [int(x) for x in (texto or "").split(",") if x.strip().isdigit()]


def lista_txt(texto):
    return [x for x in (texto or "").split(",") if x.strip()]


# ------------------------------------------------------------------- rotas
ROTAS = {}


def rota(metodo, caminho):
    def deco(f):
        ROTAS[(metodo, caminho)] = f
        return f
    return deco


@rota("GET", "/api/estado")
def r_estado(req, u, q, corpo):
    return {"tem_usuarios": db.tem_usuarios(), "usuario": u, "empresa": db.get_config("empresa", ""), "marca": marca()}


@rota("POST", "/api/setup")
def r_setup(req, u, q, c):
    if db.tem_usuarios():
        raise ErroHTTP(409, "O administrador já foi criado.")
    if c.get("senha") != c.get("senha2"):
        raise ValueError("As senhas não conferem.")
    if " " in c.get("login", "").strip():
        raise ValueError("O login não pode ter espaços.")
    db.criar_usuario(c.get("login", ""), c.get("nome", ""), c.get("senha", ""), "admin")
    db.set_config("empresa", (c.get("empresa") or "").strip() or "Minha empresa")
    return {"ok": True}


@rota("POST", "/api/login")
def r_login(req, u, q, c):
    login = (c.get("login") or "").strip().lower()
    with _trava:
        falhas, ate = _tentativas.get(login, (0, 0))
    if time.time() < ate:
        raise ErroHTTP(429, f"Muitas tentativas. Aguarde {int(ate - time.time())} s e tente de novo.")
    usuario = db.autenticar(login, c.get("senha") or "")
    if not usuario:
        with _trava:
            falhas += 1
            _tentativas[login] = (falhas, time.time() + 60 if falhas >= 5 else 0)
        raise ErroHTTP(401, "Login ou senha incorretos.")
    token = secrets.token_urlsafe(32)
    with _trava:
        _tentativas.pop(login, None)
        _sessoes[token] = {"login": usuario["login"], "expira": time.time() + DURACAO_SESSAO}
    req.novo_cookie = token
    return {"usuario": usuario_atual(usuario["login"])}


@rota("POST", "/api/logout")
def r_logout(req, u, q, c):
    with _trava:
        _sessoes.pop(req.token or "", None)
    req.novo_cookie = ""
    return {"ok": True}


@rota("GET", "/api/meta")
def r_meta(req, u, q, c):
    exigir(u)
    frutas = db.frutas_conhecidas()
    return {"fornecedores": db.listar_fornecedores(), "frutas": [{"id": f, "nome": db.nome_exibicao(f)} for f in frutas],
            "nomes": dict(db.NOMES_EXIBICAO), "limite_perda": float(db.get_config("limite_perda", "10")),
            "empresa": db.get_config("empresa", ""), "marca": marca()}


@rota("GET", "/api/linhas")
def r_linhas(req, u, q, c):
    exigir(u)
    rows = db.linhas(q.get("ini") or None, q.get("fim") or None, lista_ids(q.get("forn")) or None,
                     lista_txt(q.get("frutas")) or None)
    for r in rows:
        r["fruta_nome"] = db.nome_exibicao(r["fruta"])
    return rows


@rota("POST", "/api/contagens")
def r_registrar(req, u, q, c):
    exigir(u, "admin", "operador")
    cont = {k: v for k, v in (c.get("contagens") or {}).items()}
    lote = db.registrar_lote(int(c["fornecedor_id"]), cont, data=c.get("data") or None, origem="manual",
                             referencia=(c.get("referencia") or "").strip(), usuario=u["login"])
    return {"lote": lote}


@rota("GET", "/api/lotes/recentes")
def r_recentes(req, u, q, c):
    exigir(u)
    return db.ultimos_lotes(int(q.get("n") or 15))


@rota("GET", "/api/lotes/detalhe")
def r_detalhe(req, u, q, c):
    exigir(u)
    det = db.contagens_do_lote(int(q["id"]))
    for d in det:
        d["fruta_nome"] = db.nome_exibicao(d["fruta"])
    return det


@rota("POST", "/api/lotes/excluir")
def r_excluir(req, u, q, c):
    exigir(u, "admin")
    db.excluir_lote(int(c["lote_id"]))
    return {"ok": True}


@rota("POST", "/api/incertas")
def r_incertas(req, u, q, c):
    exigir(u, "admin", "operador")
    db.resolver_incertas(int(c["contagem_id"]), int(c.get("frescas") or 0), int(c.get("estragadas") or 0))
    return {"ok": True}


@rota("GET", "/api/fornecedores")
def r_fornecedores(req, u, q, c):
    exigir(u)
    return db.listar_fornecedores()


@rota("POST", "/api/fornecedores")
def r_salvar_fornecedor(req, u, q, c):
    exigir(u, "admin")
    fid = db.salvar_fornecedor(c.get("nome", ""), c.get("cnpj", ""), c.get("contato", ""),
                               id_=int(c["id"]) if c.get("id") else None, ativo=bool(c.get("ativo", True)))
    return {"id": fid}


@rota("GET", "/api/precos")
def r_precos(req, u, q, c):
    exigir(u)
    fid = int(q["fornecedor"])
    existentes = {p["fruta"]: p for p in db.listar_precos(fid)}
    frutas = sorted(set(db.frutas_conhecidas()) | set(existentes))
    return [{"fruta": f, "fruta_nome": db.nome_exibicao(f), "custo_unit": existentes.get(f, {}).get("custo_unit", 0.0),
             "preco_unit": existentes.get(f, {}).get("preco_unit", 0.0), "cadastrado": f in existentes} for f in frutas]


@rota("POST", "/api/precos")
def r_salvar_precos(req, u, q, c):
    exigir(u, "admin")
    fid = int(c["fornecedor_id"])
    existentes = {p["fruta"] for p in db.listar_precos(fid)}
    for item in c.get("itens", []):
        custo, preco = float(item.get("custo_unit") or 0), float(item.get("preco_unit") or 0)
        if custo > 0 or preco > 0:
            db.salvar_preco(fid, item["fruta"], custo, preco)
        elif item["fruta"] in existentes:
            db.remover_preco(fid, item["fruta"])
    return {"ok": True}


@rota("POST", "/api/config")
def r_config(req, u, q, c):
    exigir(u, "admin")
    if "limite_perda" in c:
        v = float(c["limite_perda"])
        if not 0 <= v <= 100:
            raise ValueError("O limite deve ficar entre 0 e 100%.")
        db.set_config("limite_perda", v)
    if "empresa" in c:
        db.set_config("empresa", (c["empresa"] or "").strip())
    return {"ok": True}


@rota("POST", "/api/exemplo")
def r_exemplo(req, u, q, c):
    exigir(u, "admin")
    return {"lotes": db.gerar_exemplo()}


@rota("GET", "/api/usuarios")
def r_usuarios(req, u, q, c):
    exigir(u, "admin")
    return db.listar_usuarios()


@rota("POST", "/api/usuarios")
def r_novo_usuario(req, u, q, c):
    exigir(u, "admin")
    db.criar_usuario(c.get("login", ""), c.get("nome", ""), c.get("senha", ""), c.get("perfil", "operador"))
    return {"ok": True}


@rota("POST", "/api/usuarios/ativo")
def r_usuario_ativo(req, u, q, c):
    exigir(u, "admin")
    if c.get("login") == u["login"]:
        raise ValueError("Você não pode desativar a própria conta.")
    db.definir_usuario_ativo(c["login"], bool(c.get("ativo")))
    return {"ok": True}


@rota("POST", "/api/usuarios/senha")
def r_usuario_senha(req, u, q, c):
    exigir(u, "admin")
    db.alterar_senha(c["login"], c.get("senha", ""))
    return {"ok": True}


@rota("POST", "/api/conta/senha")
def r_minha_senha(req, u, q, c):
    exigir(u)
    if db.autenticar(u["login"], c.get("atual") or "") is None:
        raise ValueError("Senha atual incorreta.")
    if c.get("nova") != c.get("nova2"):
        raise ValueError("As senhas não conferem.")
    db.alterar_senha(u["login"], c.get("nova") or "")
    return {"ok": True}



# ------------------------------------------------------------ dados da empresa
PASTA_EMPRESA = os.path.join(BASE_DIR, "dados_empresa")
MAX_LOGO = 3 * 1024 * 1024
CAMPOS_EMPRESA = {          # campo -> (chave no banco, tamanho máximo)
    "nome": ("empresa", 120), "slogan": ("empresa_slogan", 140), "descricao": ("empresa_descricao", 1200),
    "cnpj": ("empresa_cnpj", 30), "telefone": ("empresa_telefone", 40), "email": ("empresa_email", 120),
    "site": ("empresa_site", 200), "endereco": ("empresa_endereco", 300),
}
TIPOS_LOGO = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}


def tipo_imagem(dados):
    """Reconhece a imagem pelos primeiros bytes (não confia na extensão enviada)."""
    if dados.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if dados.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return "webp"
    return None


def arquivo_logo():
    nome = db.get_config("empresa_logo", "")
    caminho = os.path.join(PASTA_EMPRESA, nome) if nome else ""
    return caminho if caminho and os.path.isfile(caminho) else None


def marca(completo=False):
    dados = {k: db.get_config(chave, "") for k, (chave, _) in CAMPOS_EMPRESA.items()}
    versao = db.get_config("empresa_logo_versao", "0")
    publico = {"nome": dados["nome"], "slogan": dados["slogan"], "descricao": dados["descricao"],
               "logo_url": f"/api/empresa/logo?v={versao}" if arquivo_logo() else None}
    return dict(dados, logo_url=publico["logo_url"]) if completo else publico


@rota("GET", "/api/empresa")
def r_empresa(req, u, q, c):
    return marca(completo=u is not None)


@rota("POST", "/api/empresa")
def r_salvar_empresa(req, u, q, c):
    exigir(u, "admin")
    if "nome" in c and not str(c.get("nome") or "").strip():
        raise ValueError("Informe o nome da empresa.")
    for campo, (chave, maximo) in CAMPOS_EMPRESA.items():
        if campo in c:
            valor = str(c.get(campo) or "").strip()
            if len(valor) > maximo:
                raise ValueError(f"O campo '{campo}' aceita no máximo {maximo} caracteres.")
            db.set_config(chave, valor)
    return marca(completo=True)


@rota("POST", "/api/empresa/logo/remover")
def r_remover_logo(req, u, q, c):
    exigir(u, "admin")
    atual = arquivo_logo()
    if atual:
        os.remove(atual)
    db.set_config("empresa_logo", "")
    db.set_config("empresa_logo_versao", str(int(time.time() * 1000)))
    return marca(completo=True)

# ----------------------------------------------------------------- esteira
@rota("GET", "/api/esteira/estado")
def r_esteira_estado(req, u, q, c):
    exigir(u, "admin", "operador")
    rodando = lanc.em_execucao()
    return {"rodando": rodando, "segundos": lanc.segundos_rodando() if rodando else 0,
            "segundos_parada": lanc.segundos_desde_pedido() if rodando else 0,
            "log": lanc.ler_log(40), "resultado": None if rodando else lanc.resultado(),
            "faltando": lanc.arquivos_faltando(),
            "videos": [{"caminho": p, "nome": os.path.basename(p)} for p in lanc.videos_disponiveis()]}


@rota("POST", "/api/esteira/iniciar")
def r_esteira_iniciar(req, u, q, c):
    exigir(u, "admin", "operador")
    lanc.iniciar(int(c["fornecedor_id"]), c.get("origem"), video=c.get("video"), camera=int(c.get("camera") or 0),
                 referencia=c.get("referencia") or "", tempo_real=bool(c.get("tempo_real")))
    return {"ok": True}


@rota("POST", "/api/esteira/parar")
def r_esteira_parar(req, u, q, c):
    exigir(u, "admin", "operador")
    lanc.pedir_parada()
    return {"ok": True}


@rota("POST", "/api/esteira/forcar")
def r_esteira_forcar(req, u, q, c):
    exigir(u, "admin", "operador")
    lanc.forcar_parada()
    return {"ok": True}


# ------------------------------------------------------------------ handler
class Handler(BaseHTTPRequestHandler):
    server_version = "FrutasApp/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):          # silencia o log padrão (barulhento)
        pass

    # ---- utilidades
    def _token_cookie(self):
        for parte in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = parte.strip().partition("=")
            if k == "sessao":
                return v
        return None

    def _usuario(self):
        self.token = self._token_cookie()
        if not self.token:
            return None
        with _trava:
            s = _sessoes.get(self.token)
            if s and s["expira"] < time.time():
                _sessoes.pop(self.token, None)
                s = None
            if s:
                s["expira"] = time.time() + DURACAO_SESSAO
        return usuario_atual(s["login"]) if s else None

    def _responder(self, status, corpo, tipo="application/json; charset=utf-8", extra=None):
        dados = corpo if isinstance(corpo, bytes) else json.dumps(corpo, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        if not (extra and "Cache-Control" in extra):
            self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        if getattr(self, "novo_cookie", None) is not None:
            if self.novo_cookie:
                self.send_header("Set-Cookie", f"sessao={self.novo_cookie}; HttpOnly; SameSite=Strict; Path=/; "
                                               f"Max-Age={DURACAO_SESSAO}")
            else:
                self.send_header("Set-Cookie", "sessao=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(dados)

    def _erro(self, status, msg):
        self._responder(status, {"erro": msg})

    def _ler_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_JSON:
            raise ErroHTTP(413, "Requisição grande demais.")
        if n == 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ErroHTTP(400, "JSON inválido.")

    def _checar_origem(self):
        """Proteção CSRF: toda escrita precisa do cabeçalho X-Frutas e, se houver Origin, ele deve ser o próprio app."""
        if self.headers.get("X-Frutas") != "1":
            raise ErroHTTP(403, "Requisição recusada.")
        origem = self.headers.get("Origin")
        if origem and urlparse(origem).netloc != self.headers.get("Host"):
            raise ErroHTTP(403, "Origem não permitida.")

    # ---- métodos HTTP
    def do_GET(self):
        self._tratar("GET")

    def do_HEAD(self):
        self._tratar("GET")

    def do_POST(self):
        self._tratar("POST")

    def _tratar(self, metodo):
        self.novo_cookie = None
        url = urlparse(self.path)
        try:
            if not url.path.startswith("/api/"):
                if metodo != "GET":
                    raise ErroHTTP(405, "Método não permitido.")
                return self._estatico(url.path)
            u = self._usuario()
            if metodo == "POST":
                self._checar_origem()
            if (metodo, url.path) == ("GET", "/api/empresa/logo"):
                return self._servir_logo()
            if (metodo, url.path) == ("POST", "/api/empresa/logo"):
                exigir(u, "admin")
                return self._responder(200, self._enviar_logo())
            if (metodo, url.path) == ("POST", "/api/esteira/upload"):
                exigir(u, "admin", "operador")
                return self._responder(200, self._upload())
            f = ROTAS.get((metodo, url.path))
            if f is None:
                raise ErroHTTP(404, "Rota não encontrada.")
            q = {k: v[-1] for k, v in parse_qs(url.query).items()}
            corpo = self._ler_json() if metodo == "POST" else {}
            self._responder(200, f(self, u, q, corpo))
        except ErroHTTP as e:
            self._erro(e.status, e.msg)
        except (ValueError, KeyError, TypeError) as e:
            msg = str(e) if isinstance(e, ValueError) else f"Dado ausente ou inválido: {e}"
            self._erro(400, msg)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            traceback.print_exc()
            self._erro(500, "Erro interno. Veja a janela do servidor para detalhes.")

    def _upload(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            raise ValueError("Arquivo vazio.")
        if n > MAX_VIDEO:
            raise ErroHTTP(413, "Vídeo grande demais (limite de 4 GB).")
        nome = unquote(self.headers.get("X-Nome-Arquivo") or "video.mp4")
        if not nome.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".wmv")):
            raise ValueError("Formato não aceito. Use mp4, avi, mov, mkv ou wmv.")
        os.makedirs(lanc.PASTA_VIDEOS, exist_ok=True)
        import re
        destino = os.path.join(lanc.PASTA_VIDEOS, re.sub(r"[^\w.\- ]", "_", os.path.basename(nome)))
        restante = n
        with open(destino + ".parcial", "wb") as f:
            while restante > 0:
                bloco = self.rfile.read(min(1024 * 1024, restante))
                if not bloco:
                    break
                f.write(bloco)
                restante -= len(bloco)
        if restante:
            os.remove(destino + ".parcial")
            raise ValueError("O envio foi interrompido.")
        os.replace(destino + ".parcial", destino)
        return {"caminho": destino, "nome": os.path.basename(destino)}

    def _servir_logo(self):
        caminho = arquivo_logo()
        if not caminho:
            raise ErroHTTP(404, "Nenhuma logo cadastrada.")
        with open(caminho, "rb") as f:
            dados = f.read()
        ext = os.path.splitext(caminho)[1].lstrip(".")
        self._responder(200, dados, TIPOS_LOGO.get(ext, "application/octet-stream"),
                        {"Cache-Control": "public, max-age=31536000, immutable",
                         "Content-Security-Policy": "default-src 'none'; sandbox"})

    def _enviar_logo(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            raise ValueError("Arquivo vazio.")
        if n > MAX_LOGO:
            raise ErroHTTP(413, "Imagem grande demais (limite de 3 MB).")
        dados = self.rfile.read(n)
        tipo = tipo_imagem(dados)
        if not tipo:
            raise ValueError("Formato não aceito. Envie uma imagem PNG, JPG ou WEBP.")
        os.makedirs(PASTA_EMPRESA, exist_ok=True)
        anterior = arquivo_logo()
        nome = f"logo.{tipo}"
        temp = os.path.join(PASTA_EMPRESA, nome + ".parcial")
        with open(temp, "wb") as f:
            f.write(dados)
        os.replace(temp, os.path.join(PASTA_EMPRESA, nome))
        if anterior and os.path.basename(anterior) != nome:
            os.remove(anterior)
        db.set_config("empresa_logo", nome)
        db.set_config("empresa_logo_versao", str(int(time.time() * 1000)))
        return marca(completo=True)

    def _estatico(self, caminho):
        rel = unquote(caminho).lstrip("/") or "index.html"
        alvo = os.path.realpath(os.path.join(PASTA_WEB, rel))
        if not alvo.startswith(os.path.realpath(PASTA_WEB) + os.sep) or not os.path.isfile(alvo):
            alvo = os.path.join(PASTA_WEB, "index.html")       # rotas do app caem na página principal
        with open(alvo, "rb") as f:
            dados = f.read()
        tipo = mimetypes.guess_type(alvo)[0] or "application/octet-stream"
        if tipo.startswith("text/") or tipo in ("application/javascript", "application/json"):
            tipo += "; charset=utf-8"
        self._responder(200, dados, tipo)


def porta_livre(host, porta):
    for p in range(porta, porta + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    raise SystemExit(f"Nenhuma porta livre entre {porta} e {porta + 19}.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--porta", type=int, default=8600)
    ap.add_argument("--rede", action="store_true", help="aceita conexões de outros computadores da rede")
    ap.add_argument("--sem-navegador", action="store_true")
    args, _ = ap.parse_known_args()

    if not os.path.isfile(os.path.join(PASTA_WEB, "index.html")):
        raise SystemExit(f"Pasta da interface não encontrada: {PASTA_WEB}\n"
                         "Copie a pasta 'web' (index.html, app.js, style.css) para junto deste arquivo.")
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    db.iniciar()
    host = "0.0.0.0" if args.rede else "127.0.0.1"
    porta = porta_livre(host, args.porta)
    servidor = ThreadingHTTPServer((host, porta), Handler)
    servidor.daemon_threads = True
    url = f"http://localhost:{porta}"
    print(f"App de frutas rodando em {url}")
    if args.rede:
        print(f"Na rede: http://{socket.gethostbyname(socket.gethostname())}:{porta}")
    print("Para encerrar: feche esta janela ou aperte Ctrl+C.")
    if not args.sem_navegador:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
        print("Servidor encerrado.")


if __name__ == "__main__":
    main()
