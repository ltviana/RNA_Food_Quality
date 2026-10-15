"""
Camada de dados do sistema de controle de qualidade de frutas (SQLite, sem dependências extras).

Usada por:
  - app_frutas.py  (aplicativo com login e dashboard)
  - esteira.py     (grava a contagem da esteira direto no banco: --fornecedor "Nome")

O banco fica em  frutas.db  (mesma pasta dos scripts) ou no caminho da variável FRUTAS_DB.

Modelo:
  usuarios     login, senha (PBKDF2 com sal), perfil (admin / operador / visualizador)
  fornecedores nome, CNPJ, contato, ativo
  precos       custo de compra e preço de venda POR FRUTA e FORNECEDOR (por unidade)
  lotes        uma carga/contagem: data, fornecedor, origem (manual / esteira), referência
  contagens    por lote e fruta: frescas, estragadas, incertas + custo e preço no momento
               (guardados na própria contagem: mudar o preço depois NÃO altera o histórico)
"""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()
DB_PATH = os.environ.get("FRUTAS_DB", os.path.join(BASE_DIR, "frutas.db"))

PERFIS = ("admin", "operador", "visualizador")
ITER_SENHA = 200_000

# Frutas/vegetais conhecidos (usados se classes_frutas.json não existir)
FRUTAS_PADRAO = ["Apple", "Banana", "Carrot", "Cucumber", "Grape", "Mango", "Orange",
                 "Potato", "Strawberry", "Tomato"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    perfil TEXT NOT NULL,
    sal TEXT NOT NULL,
    hash TEXT NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fornecedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL,
    cnpj TEXT DEFAULT '',
    contato TEXT DEFAULT '',
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS precos (
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id),
    fruta TEXT NOT NULL,
    custo_unit REAL NOT NULL,
    preco_unit REAL NOT NULL,
    PRIMARY KEY (fornecedor_id, fruta)
);
CREATE TABLE IF NOT EXISTS lotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id),
    origem TEXT NOT NULL DEFAULT 'manual',
    referencia TEXT DEFAULT '',
    usuario TEXT DEFAULT '',
    criado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contagens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lote_id INTEGER NOT NULL REFERENCES lotes(id) ON DELETE CASCADE,
    fruta TEXT NOT NULL,
    frescas INTEGER NOT NULL DEFAULT 0,
    estragadas INTEGER NOT NULL DEFAULT 0,
    incertas INTEGER NOT NULL DEFAULT 0,
    custo_unit REAL NOT NULL DEFAULT 0,
    preco_unit REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_lotes_data ON lotes(data);
CREATE INDEX IF NOT EXISTS ix_contagens_lote ON contagens(lote_id);
CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT NOT NULL);
"""


# ------------------------------------------------------------------ conexão
@contextmanager
def conexao(caminho=None):
    con = sqlite3.connect(caminho or DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def iniciar(caminho=None):
    with conexao(caminho) as con:
        con.executescript(SCHEMA)


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# -------------------------------------------------------------------- senhas
def _hash(senha, sal):
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(sal), ITER_SENHA).hex()


def senha_valida(senha):
    """Retorna mensagem de erro, ou None se a senha é aceitável."""
    if len(senha) < 8:
        return "A senha precisa ter pelo menos 8 caracteres."
    if senha.lower() == senha or not any(c.isdigit() for c in senha):
        return "Use letras maiúsculas e minúsculas e pelo menos um número."
    return None


def criar_usuario(login, nome, senha, perfil="operador", caminho=None):
    login = login.strip().lower()
    if not login or not nome.strip():
        raise ValueError("Informe login e nome.")
    if perfil not in PERFIS:
        raise ValueError("Perfil inválido.")
    erro = senha_valida(senha)
    if erro:
        raise ValueError(erro)
    sal = secrets.token_hex(16)
    try:
        with conexao(caminho) as con:
            con.execute("INSERT INTO usuarios (login, nome, perfil, sal, hash, criado_em) VALUES (?,?,?,?,?,?)",
                        (login, nome.strip(), perfil, sal, _hash(senha, sal), agora()))
    except sqlite3.IntegrityError:
        raise ValueError(f"O login '{login}' já existe.")


def autenticar(login, senha, caminho=None):
    """Devolve o usuário (dict) se login/senha estiverem corretos, senão None."""
    with conexao(caminho) as con:
        u = con.execute("SELECT * FROM usuarios WHERE login=? AND ativo=1", (login.strip().lower(),)).fetchone()
    if u is None:
        _hash(senha, "00" * 16)          # gasta o mesmo tempo, para não revelar se o login existe
        return None
    if hmac.compare_digest(_hash(senha, u["sal"]), u["hash"]):
        return {"id": u["id"], "login": u["login"], "nome": u["nome"], "perfil": u["perfil"]}
    return None


def alterar_senha(login, nova, caminho=None):
    erro = senha_valida(nova)
    if erro:
        raise ValueError(erro)
    sal = secrets.token_hex(16)
    with conexao(caminho) as con:
        con.execute("UPDATE usuarios SET sal=?, hash=? WHERE login=?", (sal, _hash(nova, sal), login.strip().lower()))


def tem_usuarios(caminho=None):
    with conexao(caminho) as con:
        return con.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] > 0


def listar_usuarios(caminho=None):
    with conexao(caminho) as con:
        return [dict(r) for r in con.execute(
            "SELECT id, login, nome, perfil, ativo, criado_em FROM usuarios ORDER BY login")]


def definir_usuario_ativo(login, ativo, caminho=None):
    with conexao(caminho) as con:
        if not ativo:       # nunca desativa o último admin
            admins = con.execute("SELECT COUNT(*) FROM usuarios WHERE perfil='admin' AND ativo=1 AND login<>?",
                                 (login,)).fetchone()[0]
            alvo = con.execute("SELECT perfil FROM usuarios WHERE login=?", (login,)).fetchone()
            if alvo and alvo["perfil"] == "admin" and admins == 0:
                raise ValueError("Não é possível desativar o único administrador.")
        con.execute("UPDATE usuarios SET ativo=? WHERE login=?", (1 if ativo else 0, login))


# --------------------------------------------------------------- fornecedores
def salvar_fornecedor(nome, cnpj="", contato="", id_=None, ativo=True, caminho=None):
    nome = nome.strip()
    if not nome:
        raise ValueError("Informe o nome do fornecedor.")
    try:
        with conexao(caminho) as con:
            if id_ is None:
                cur = con.execute("INSERT INTO fornecedores (nome, cnpj, contato, ativo, criado_em) VALUES (?,?,?,?,?)",
                                  (nome, cnpj.strip(), contato.strip(), 1 if ativo else 0, agora()))
                return cur.lastrowid
            con.execute("UPDATE fornecedores SET nome=?, cnpj=?, contato=?, ativo=? WHERE id=?",
                        (nome, cnpj.strip(), contato.strip(), 1 if ativo else 0, id_))
            return id_
    except sqlite3.IntegrityError:
        raise ValueError(f"Já existe um fornecedor chamado '{nome}'.")


def listar_fornecedores(somente_ativos=False, caminho=None):
    with conexao(caminho) as con:
        q = "SELECT * FROM fornecedores" + (" WHERE ativo=1" if somente_ativos else "") + " ORDER BY nome"
        return [dict(r) for r in con.execute(q)]


def achar_fornecedor(texto, caminho=None):
    """Aceita id numérico ou nome (sem diferenciar maiúsculas). Devolve dict ou None."""
    with conexao(caminho) as con:
        if str(texto).isdigit():
            r = con.execute("SELECT * FROM fornecedores WHERE id=?", (int(texto),)).fetchone()
            if r:
                return dict(r)
        r = con.execute("SELECT * FROM fornecedores WHERE lower(nome)=lower(?)", (str(texto).strip(),)).fetchone()
        return dict(r) if r else None


# --------------------------------------------------------------------- preços
def salvar_preco(fornecedor_id, fruta, custo_unit, preco_unit, caminho=None):
    if custo_unit < 0 or preco_unit < 0:
        raise ValueError("Valores não podem ser negativos.")
    with conexao(caminho) as con:
        con.execute("""INSERT INTO precos (fornecedor_id, fruta, custo_unit, preco_unit) VALUES (?,?,?,?)
                       ON CONFLICT(fornecedor_id, fruta) DO UPDATE SET custo_unit=excluded.custo_unit,
                       preco_unit=excluded.preco_unit""", (fornecedor_id, fruta, float(custo_unit), float(preco_unit)))


def remover_preco(fornecedor_id, fruta, caminho=None):
    with conexao(caminho) as con:
        con.execute("DELETE FROM precos WHERE fornecedor_id=? AND fruta=?", (fornecedor_id, fruta))


def listar_precos(fornecedor_id=None, caminho=None):
    with conexao(caminho) as con:
        q = ("SELECT p.fornecedor_id, f.nome AS fornecedor, p.fruta, p.custo_unit, p.preco_unit "
             "FROM precos p JOIN fornecedores f ON f.id=p.fornecedor_id")
        args = ()
        if fornecedor_id is not None:
            q += " WHERE p.fornecedor_id=?"
            args = (fornecedor_id,)
        return [dict(r) for r in con.execute(q + " ORDER BY f.nome, p.fruta", args)]


def preco_de(fornecedor_id, fruta, caminho=None):
    with conexao(caminho) as con:
        r = con.execute("SELECT custo_unit, preco_unit FROM precos WHERE fornecedor_id=? AND fruta=?",
                        (fornecedor_id, fruta)).fetchone()
    return (r["custo_unit"], r["preco_unit"]) if r else (0.0, 0.0)


# ------------------------------------------------------------- lotes/contagens
def registrar_lote(fornecedor_id, contagens, data=None, origem="manual", referencia="", usuario="", caminho=None):
    """contagens: {fruta: (frescas, estragadas, incertas)} ou {fruta: {"frescas":..,"estragadas":..,"incertas":..}}.
    Custo e preço são copiados da tabela de preços do fornecedor NO MOMENTO do registro.
    Devolve o id do lote."""
    itens = []
    for fruta, v in contagens.items():
        if isinstance(v, dict):
            fr, es, inc = v.get("frescas", 0), v.get("estragadas", 0), v.get("incertas", 0)
        else:
            fr, es, inc = (list(v) + [0, 0, 0])[:3]
        fr, es, inc = int(fr), int(es), int(inc)
        if min(fr, es, inc) < 0:
            raise ValueError("As quantidades não podem ser negativas.")
        if fr + es + inc > 0:
            itens.append((fruta, fr, es, inc))
    if not itens:
        raise ValueError("Nenhuma quantidade informada.")
    data = str(data or date.today())
    with conexao(caminho) as con:
        if con.execute("SELECT 1 FROM fornecedores WHERE id=?", (fornecedor_id,)).fetchone() is None:
            raise ValueError("Fornecedor não encontrado.")
        cur = con.execute("INSERT INTO lotes (data, fornecedor_id, origem, referencia, usuario, criado_em) "
                          "VALUES (?,?,?,?,?,?)", (data, fornecedor_id, origem, referencia, usuario, agora()))
        lote = cur.lastrowid
        for fruta, fr, es, inc in itens:
            p = con.execute("SELECT custo_unit, preco_unit FROM precos WHERE fornecedor_id=? AND fruta=?",
                            (fornecedor_id, fruta)).fetchone()
            custo, preco = (p["custo_unit"], p["preco_unit"]) if p else (0.0, 0.0)
            con.execute("INSERT INTO contagens (lote_id, fruta, frescas, estragadas, incertas, custo_unit, preco_unit) "
                        "VALUES (?,?,?,?,?,?,?)", (lote, fruta, fr, es, inc, custo, preco))
    return lote


def excluir_lote(lote_id, caminho=None):
    with conexao(caminho) as con:
        con.execute("DELETE FROM contagens WHERE lote_id=?", (lote_id,))
        con.execute("DELETE FROM lotes WHERE id=?", (lote_id,))


def resolver_incertas(contagem_id, para_frescas, para_estragadas, caminho=None):
    """Revisão manual: converte frutas 'incertas' em frescas/estragadas."""
    with conexao(caminho) as con:
        r = con.execute("SELECT incertas FROM contagens WHERE id=?", (contagem_id,)).fetchone()
        if r is None:
            raise ValueError("Contagem não encontrada.")
        if para_frescas < 0 or para_estragadas < 0 or para_frescas + para_estragadas > r["incertas"]:
            raise ValueError(f"Só há {r['incertas']} incertas nesta contagem.")
        con.execute("UPDATE contagens SET incertas=incertas-?, frescas=frescas+?, estragadas=estragadas+? WHERE id=?",
                    (para_frescas + para_estragadas, para_frescas, para_estragadas, contagem_id))


def linhas(data_ini=None, data_fim=None, fornecedores=None, frutas=None, caminho=None):
    """Uma linha por (lote, fruta) já com as métricas financeiras calculadas. Lista de dicts."""
    q = """SELECT c.id AS contagem_id, l.id AS lote_id, l.data, l.origem, l.referencia, l.usuario,
                   f.id AS fornecedor_id, f.nome AS fornecedor, c.fruta,
                   c.frescas, c.estragadas, c.incertas, c.custo_unit, c.preco_unit
            FROM contagens c JOIN lotes l ON l.id=c.lote_id JOIN fornecedores f ON f.id=l.fornecedor_id WHERE 1=1"""
    args = []
    if data_ini:
        q += " AND l.data>=?"; args.append(str(data_ini))
    if data_fim:
        q += " AND l.data<=?"; args.append(str(data_fim))
    if fornecedores:
        q += f" AND f.id IN ({','.join('?' * len(fornecedores))})"; args += list(fornecedores)
    if frutas:
        q += f" AND c.fruta IN ({','.join('?' * len(frutas))})"; args += list(frutas)
    with conexao(caminho) as con:
        rows = [dict(r) for r in con.execute(q + " ORDER BY l.data, l.id", args)]
    for r in rows:
        r.update(metricas(r["frescas"], r["estragadas"], r["incertas"], r["custo_unit"], r["preco_unit"]))
    return rows


def metricas(frescas, estragadas, incertas, custo_unit, preco_unit):
    """Definições (todas por unidade de fruta):
      total              = frescas + estragadas + incertas
      custo_total        = total * custo de compra
      receita_potencial  = total * preço de venda            (se nada estragasse)
      receita_realizada  = frescas * preço de venda
      receita_perdida    = estragadas * preço de venda
      custo_perdido      = estragadas * custo de compra       (dinheiro pago por fruta que não vendeu)
      lucro_realizado    = receita_realizada - custo_total
      receita_em_revisao = incertas * preço de venda          (ainda sem classificação definitiva)
    """
    total = frescas + estragadas + incertas
    return {
        "total": total,
        "custo_total": total * custo_unit,
        "receita_potencial": total * preco_unit,
        "receita_realizada": frescas * preco_unit,
        "receita_perdida": estragadas * preco_unit,
        "custo_perdido": estragadas * custo_unit,
        "receita_em_revisao": incertas * preco_unit,
        "lucro_realizado": frescas * preco_unit - total * custo_unit,
    }


def frutas_conhecidas():
    """Lista de frutas: lê classes_frutas.json (gerado pelo treino) ou usa a lista padrão."""
    for nome in ("classes_frutas.json",):
        caminho = os.path.join(BASE_DIR, nome)
        if os.path.exists(caminho):
            try:
                with open(caminho, encoding="utf-8") as f:
                    dados = json.load(f)
                itens = dados.get("classes", dados) if isinstance(dados, dict) else dados
                nomes = sorted({i["fruit"] for i in itens if isinstance(i, dict) and i.get("fruit")})
                if nomes:
                    return nomes
            except Exception:
                pass
    return list(FRUTAS_PADRAO)


# ------------------------------------------------------------ dados de exemplo
def gerar_exemplo(dias=90, semente=7, caminho=None):
    """Cria fornecedores, preços e lotes fictícios para o dashboard ter o que mostrar."""
    import random
    rnd = random.Random(semente)
    perfil = {   # fornecedor: (taxa de perda, [(fruta, custo, preço)])
        "Fazenda Boa Safra": (0.05, [("Banana", 1.10, 2.20), ("Tomato", 1.80, 3.60), ("Carrot", 0.90, 1.90)]),
        "Hortifruti Vale Verde": (0.11, [("Tomato", 1.60, 3.60), ("Cucumber", 1.00, 2.20), ("Carrot", 0.80, 1.90)]),
        "Cooperativa Sol Nascente": (0.18, [("Banana", 0.95, 2.20), ("Cucumber", 0.85, 2.20), ("Apple", 1.70, 3.90)]),
    }
    ids = {}
    for nome, (_, precos) in perfil.items():
        f = achar_fornecedor(nome, caminho)
        ids[nome] = f["id"] if f else salvar_fornecedor(nome, caminho=caminho)
        for fruta, custo, preco in precos:
            salvar_preco(ids[nome], fruta, custo, preco, caminho)
    hoje = date.today()
    n = 0
    for d in range(dias, -1, -1):
        dia = hoje - timedelta(days=d)
        if dia.weekday() == 6:
            continue
        for nome, (taxa, precos) in perfil.items():
            if rnd.random() < 0.45:
                continue
            tendencia = 1 + 0.25 * (1 - d / dias) * (1 if nome.startswith("Coop") else -0.4)
            cont = {}
            for fruta, _, _ in precos:
                total = rnd.randint(120, 420)
                p = min(0.6, max(0.01, rnd.gauss(taxa * tendencia, 0.025)))
                est = int(total * p)
                inc = int(total * rnd.uniform(0.005, 0.03))
                cont[fruta] = (total - est - inc, est, inc)
            registrar_lote(ids[nome], cont, data=dia, origem="exemplo", referencia=f"EX-{n:04d}", caminho=caminho)
            n += 1
    return n


# ------------------------------------------------------------------ extras
NOMES_EXIBICAO = {
    "apple": "Maçã", "banana": "Banana", "orange": "Laranja", "mango": "Manga", "strawberry": "Morango",
    "grape": "Uva", "grapes": "Uva", "pear": "Pera", "lemon": "Limão", "watermelon": "Melancia",
    "pineapple": "Abacaxi", "papaya": "Mamão", "peach": "Pêssego", "pomegranate": "Romã", "kiwi": "Kiwi",
    "tomato": "Tomate", "potato": "Batata", "carrot": "Cenoura", "cucumber": "Pepino",
    "bellpepper": "Pimentão", "capsicum": "Pimentão", "okra": "Quiabo", "guava": "Goiaba",
    "jujube": "Jujuba", "bittergourd": "Melão amargo", "broccoli": "Brócolis",
}


def nome_exibicao(fruta):
    return NOMES_EXIBICAO.get(str(fruta).lower(), str(fruta))


def get_config(chave, padrao=None, caminho=None):
    with conexao(caminho) as con:
        r = con.execute("SELECT valor FROM config WHERE chave=?", (chave,)).fetchone()
    return r["valor"] if r else padrao


def set_config(chave, valor, caminho=None):
    with conexao(caminho) as con:
        con.execute("INSERT INTO config (chave, valor) VALUES (?,?) "
                    "ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor", (chave, str(valor)))


def registrar_contagem_esteira(fornecedor, contagens, referencia="", usuario="esteira", caminho=None):
    """Atalho para a esteira: `fornecedor` = nome ou id; cria o fornecedor se ainda não existir."""
    iniciar(caminho)
    f = achar_fornecedor(fornecedor, caminho)
    if f is None:
        if str(fornecedor).isdigit():
            raise ValueError(f"Fornecedor de id {fornecedor} não existe. Cadastre-o no aplicativo.")
        fid = salvar_fornecedor(str(fornecedor), caminho=caminho)
    else:
        fid = f["id"]
    return registrar_lote(fid, contagens, origem="esteira", referencia=referencia, usuario=usuario, caminho=caminho)


def ultimos_lotes(n=15, caminho=None):
    """Lotes mais recentes (qualquer origem: manual, esteira, exemplo), com totais, do mais novo para o mais antigo."""
    q = """SELECT l.id AS lote_id, l.data, l.criado_em, f.nome AS fornecedor, l.origem, l.referencia, l.usuario,
                  COALESCE(SUM(c.frescas),0) AS frescas, COALESCE(SUM(c.estragadas),0) AS estragadas,
                  COALESCE(SUM(c.incertas),0) AS incertas
           FROM lotes l JOIN fornecedores f ON f.id=l.fornecedor_id LEFT JOIN contagens c ON c.lote_id=l.id
           GROUP BY l.id ORDER BY l.id DESC LIMIT ?"""
    with conexao(caminho) as con:
        return [dict(r) for r in con.execute(q, (int(n),))]


def contagens_do_lote(lote_id, caminho=None):
    with conexao(caminho) as con:
        return [dict(r) for r in con.execute(
            "SELECT fruta, frescas, estragadas, incertas FROM contagens WHERE lote_id=? ORDER BY fruta", (lote_id,))]
