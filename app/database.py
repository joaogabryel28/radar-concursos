import json
import os
import sqlite3
from datetime import datetime, timedelta

from .config import DATA_DIR, DB_PATH, EM_VERCEL

STATUS_ORDEM = {
    "previsto": 0, "autorizado": 1, "edital_publicado": 2,
    "inscricoes_abertas": 3, "encerrado": 4,
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS concursos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fingerprint TEXT UNIQUE,
  orgao TEXT NOT NULL,
  descricao TEXT,
  nivel TEXT,
  uf TEXT,
  municipio TEXT,
  banca TEXT,
  status TEXT DEFAULT 'edital_publicado',
  vagas INTEGER,
  salario_max REAL,
  data_inscricoes TEXT,
  data_prova TEXT,
  edital_url TEXT,
  inscricoes_url TEXT,
  fonte_url TEXT,
  fonte_nome TEXT,
  resumo TEXT,
  areas TEXT DEFAULT '[]',
  cursos TEXT DEFAULT '[]',
  primeira_deteccao TEXT,
  ultima_atualizacao TEXT,
  raw TEXT
);
CREATE INDEX IF NOT EXISTS idx_concursos_status ON concursos(status);
CREATE INDEX IF NOT EXISTS idx_concursos_uf ON concursos(uf);
CREATE INDEX IF NOT EXISTS idx_concursos_deteccao ON concursos(primeira_deteccao);

CREATE TABLE IF NOT EXISTS eventos_fonte (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fonte TEXT NOT NULL,
  url TEXT NOT NULL UNIQUE,
  concurso_id INTEGER,
  primeira_deteccao TEXT
);

CREATE TABLE IF NOT EXISTS execucoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fonte TEXT, inicio TEXT, fim TEXT,
  itens_vistos INTEGER DEFAULT 0, itens_novos INTEGER DEFAULT 0,
  ok INTEGER DEFAULT 1, erro TEXT
);
"""


def conectar() -> sqlite3.Connection:
    if EM_VERCEL:
        # filesystem do serverless e somente-leitura: immutable=1 dispensa a
        # criacao de -shm/-wal (impossivel em ro), exigida por bancos em modo WAL
        c = sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True, timeout=30)
    else:
        c = sqlite3.connect(DB_PATH, timeout=30)
        c.execute("PRAGMA journal_mode=WAL")
    c.row_factory = sqlite3.Row
    return c


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with conectar() as c:
        c.executescript(SCHEMA)


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def upsert_concurso(d: dict):
    """Insere ou mescla um concurso. Retorna (id, criado)."""
    with conectar() as c:
        row = c.execute(
            "SELECT * FROM concursos WHERE fingerprint=?", (d["fingerprint"],)
        ).fetchone()

        if row is None:
            colunas = [
                "fingerprint", "orgao", "descricao", "nivel", "uf", "municipio",
                "banca", "status", "vagas", "salario_max", "data_inscricoes",
                "data_prova", "edital_url", "inscricoes_url", "fonte_url",
                "fonte_nome", "resumo", "areas", "cursos", "raw",
            ]
            valores = []
            for campo in colunas:
                v = d.get(campo)
                if campo in ("areas", "cursos"):
                    v = json.dumps(v or [], ensure_ascii=False)
                valores.append(v)
            cur = c.execute(
                f"INSERT INTO concursos ({', '.join(colunas)}, primeira_deteccao, ultima_atualizacao) "
                f"VALUES ({', '.join('?' * len(colunas))}, ?, ?)",
                [*valores, _agora(), _agora()],
            )
            return cur.lastrowid, True

        e = dict(row)
        mesclado = e
        mesclado["status"] = max(
            [e.get("status") or "edital_publicado", d.get("status") or e.get("status")],
            key=lambda s: STATUS_ORDEM.get(s, 0),
        )
        for campo in ("orgao", "descricao", "nivel", "uf", "municipio", "banca",
                      "edital_url", "inscricoes_url", "fonte_url", "fonte_nome"):
            novo = d.get(campo)
            if novo and (not e.get(campo) or (campo == "descricao" and len(str(novo)) > len(str(e.get(campo) or "")))):
                mesclado[campo] = novo
        for campo in ("vagas", "salario_max"):
            candidatos = [v for v in (e.get(campo), d.get(campo)) if v]
            mesclado[campo] = max(candidatos) if candidatos else None
        for campo in ("data_inscricoes", "data_prova"):
            mesclado[campo] = d.get(campo) or e.get(campo)
        for campo in ("areas", "cursos"):
            velho = set(json.loads(e.get(campo) or "[]"))
            mesclado[campo] = json.dumps(
                sorted(velho | set(d.get(campo) or [])), ensure_ascii=False
            )

        c.execute(
            """UPDATE concursos SET orgao=?, descricao=?, nivel=?, uf=?, municipio=?,
               banca=?, status=?, vagas=?, salario_max=?, data_inscricoes=?,
               data_prova=?, edital_url=?, inscricoes_url=?, fonte_url=?, fonte_nome=?,
               resumo=COALESCE(?, resumo), areas=?, cursos=?, ultima_atualizacao=?
               WHERE id=?""",
            (
                mesclado.get("orgao"), mesclado.get("descricao"), mesclado.get("nivel"),
                mesclado.get("uf"), mesclado.get("municipio"), mesclado.get("banca"),
                mesclado.get("status"), mesclado.get("vagas"), mesclado.get("salario_max"),
                mesclado.get("data_inscricoes"), mesclado.get("data_prova"),
                mesclado.get("edital_url"), mesclado.get("inscricoes_url"),
                mesclado.get("fonte_url"), mesclado.get("fonte_nome"),
                d.get("resumo"), mesclado.get("areas"), mesclado.get("cursos"),
                _agora(), e["id"],
            ),
        )
        return e["id"], False


def url_ja_vista(fonte: str, url: str) -> bool:
    with conectar() as c:
        return c.execute(
            "SELECT 1 FROM eventos_fonte WHERE fonte=? AND url=?", (fonte, url)
        ).fetchone() is not None


def registrar_evento_fonte(fonte: str, url: str, concurso_id: int) -> bool:
    try:
        with conectar() as c:
            c.execute(
                "INSERT INTO eventos_fonte (fonte, url, concurso_id, primeira_deteccao) VALUES (?,?,?,?)",
                (fonte, url, concurso_id, _agora()),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def registrar_execucao(fonte: str, inicio: str, vistos: int, novos: int, erro=None):
    with conectar() as c:
        c.execute(
            "INSERT INTO execucoes (fonte, inicio, fim, itens_vistos, itens_novos, ok, erro) VALUES (?,?,?,?,?,?,?)",
            (fonte, inicio, _agora(), vistos, novos, erro is None, erro),
        )


def _linhas_para_dicts(c, rows) -> list:
    itens = []
    for r in rows:
        d = dict(r)
        for campo in ("areas", "cursos"):
            d[campo] = json.loads(d.get(campo) or "[]")
        itens.append(d)
    return itens


def listar_concursos(aba="abertas", uf=None, area=None, curso=None, nivel=None,
                     q=None, novos_dias=None, ordem="recentes", limite=200) -> list:
    where, params = ["1=1"], []
    if aba == "abertas":
        where.append("status='inscricoes_abertas'")
    elif aba == "publicados":
        where.append("status='edital_publicado'")
    elif aba == "previstos":
        where.append("status IN ('previsto','autorizado')")
    if uf:
        where.append("uf=?")
        params.append(uf.upper())
    if nivel:
        where.append("nivel=?")
        params.append(nivel)
    if area:
        where.append("areas LIKE ?")
        params.append(f'%"{area}"%')
    if curso:
        where.append("cursos LIKE ?")
        params.append(f'%"{curso}"%')
    if q:
        where.append("(orgao LIKE ? OR descricao LIKE ? OR resumo LIKE ?)")
        params.extend([f"%{q}%"] * 3)
    if novos_dias:
        limite_data = (datetime.now() - timedelta(days=novos_dias)).isoformat(timespec="seconds")
        where.append("primeira_deteccao >= ?")
        params.append(limite_data)
    if ordem == "antigos":
        ordenacao = "primeira_deteccao ASC, id ASC"
    else:
        ordenacao = "primeira_deteccao DESC, id DESC"
    sql = (
        "SELECT * FROM concursos WHERE " + " AND ".join(where) +
        f" ORDER BY {ordenacao} LIMIT ?"
    )
    params.append(int(limite))
    with conectar() as c:
        return _linhas_para_dicts(c, c.execute(sql, params).fetchall())


def obter_concurso(id_: int):
    with conectar() as c:
        r = c.execute("SELECT * FROM concursos WHERE id=?", (id_,)).fetchone()
        return _linhas_para_dicts(c, [r])[0] if r else None


def meta() -> dict:
    with conectar() as c:
        contagens = {
            r[0]: r[1] for r in c.execute("SELECT status, COUNT(*) FROM concursos GROUP BY status")
        }
        corte_7d = (datetime.now() - timedelta(days=7)).isoformat(timespec="seconds")
        novos7 = c.execute(
            "SELECT COUNT(*) FROM concursos WHERE primeira_deteccao >= ?", (corte_7d,)
        ).fetchone()[0]
        ufs = [r[0] for r in c.execute(
            "SELECT DISTINCT uf FROM concursos WHERE uf IS NOT NULL ORDER BY uf"
        )]
        ultimas = {r[0]: r[1] for r in c.execute(
            "SELECT fonte, MAX(fim) FROM execucoes GROUP BY fonte"
        )}
    return {"contagens": contagens, "novos_7d": novos7, "ufs": ufs, "ultima_coleta": ultimas}
