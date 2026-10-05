"""Pipeline: recebe eventos dos coletores, tria, classifica, extrai campos e grava."""
import hashlib
import json
import re
import threading
from datetime import datetime

from . import classify, database, extract
from .collectors import dou, fcc, googlenews, ibfc, queridodiario

COLETORES = {
    "dou": dou.coletar,
    "queridodiario": queridodiario.coletar,
    "fcc": fcc.coletar,
    "ibfc": ibfc.coletar,
    "googlenews": googlenews.coletar,
}

coleta_lock = threading.Lock()


def limpar_titulo(t: str) -> str:
    t = re.sub(r"\s+", " ", t or "").strip()
    t = re.sub(
        r"^(edital( de abertura)?( n[ºo°.]?\s*[\d/.]+( de [^,;.]+)?)?[-–—:]?\s*)", "",
        t, flags=re.I,
    )
    t = re.sub(r"^(concurso publico|processo seletivo|certame)[-–—:]?\s*", "", t, flags=re.I)
    return t.strip(" -–—")[:140]


def _ano_em(texto: str) -> str:
    m = re.search(r"\b(20[12]\d)\b", texto or "")
    return m.group(1) if m else str(datetime.now().year)


def fingerprint(orgao: str, uf, municipio, texto: str) -> str:
    base = (
        classify.normalizar(orgao)[:60] + "|" + (uf or "") + "|" +
        classify.normalizar(municipio or "")[:40] + "|" + _ano_em(texto)
    )
    return hashlib.sha1(base.encode()).hexdigest()[:16]


def normalizar_data(valor):
    if not valor:
        return None
    valor = str(valor).strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})", valor)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)}/{m.group(2)}/{m.group(3)}", "%d/%m/%Y").date().isoformat()
        except ValueError:
            return None
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(valor).date().isoformat()
    except Exception:
        pass
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", valor)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def processar(ev: dict):
    """Retorna True se o concurso e novo no banco, False se mesclado/ja visto."""
    fonte = ev.get("fonte")
    url = ev.get("url")
    if not fonte or not url:
        return False
    if database.url_ja_vista(fonte, url):
        return False

    texto = " ".join(filter(None, [ev.get("titulo"), ev.get("texto")]))
    eh_concurso, status = classify.triagem(texto, ev.get("status_padrao", "edital_publicado"))
    if not eh_concurso:
        database.registrar_evento_fonte(fonte, url, None)
        return False

    orgao = ev.get("orgao") or limpar_titulo(ev.get("titulo") or "Concurso público")
    uf = ev.get("uf") or classify.detectar_uf(texto)
    municipio = ev.get("municipio")
    nivel = ev.get("nivel") or classify.detectar_nivel(texto)
    areas = classify.tag_areas(texto)
    cursos = classify.tag_cursos(texto)

    edital_url = ev.get("edital_url") or ev.get("pdf_url")
    campos = {}
    texto_pdf = None
    if ev.get("pdf_url"):
        texto_pdf = extract.texto_do_pdf(extract.baixar_pdf(ev["pdf_url"]))
        if texto_pdf:
            campos = extract.extrair_campos(texto_pdf)
    campos_titulo = extract.extrair_campos(texto) if texto else {}
    for chave in ("vagas", "salario_max", "data_inscricoes", "data_prova"):
        if not campos.get(chave):
            campos[chave] = campos_titulo.get(chave)
    if not campos.get("resumo"):
        resumo = re.sub(r"\s+", " ", ev.get("texto") or "").strip()
        campos["resumo"] = resumo[:400] or None
    if texto_pdf:
        texto_completo = texto + " " + texto_pdf[:60_000]
        areas = classify.tag_areas(texto_completo)
        cursos = classify.tag_cursos(texto_completo)

    registro = {
        "fingerprint": fingerprint(orgao, uf, municipio, texto),
        "orgao": orgao,
        "descricao": limpar_titulo(ev.get("titulo")) or None,
        "nivel": nivel,
        "uf": uf,
        "municipio": municipio,
        "banca": ev.get("banca"),
        "status": status,
        "edital_url": edital_url,
        "inscricoes_url": ev.get("inscricoes_url"),
        "fonte_url": ev.get("fonte_url") or url,
        "fonte_nome": ev.get("fonte_nome"),
        "resumo": campos.get("resumo"),
        "vagas": campos.get("vagas"),
        "salario_max": campos.get("salario_max"),
        "data_inscricoes": campos.get("data_inscricoes"),
        "data_prova": campos.get("data_prova"),
        "areas": areas,
        "cursos": cursos,
        "raw": json.dumps(ev, ensure_ascii=False)[:4000],
    }
    id_, criado = database.upsert_concurso(registro)
    database.registrar_evento_fonte(fonte, url, id_)
    return criado


def rodar_coleta(fontes=None) -> dict:
    if not coleta_lock.acquire(blocking=False):
        return {"_erro": "coleta já em execução"}
    try:
        resumo = {}
        for nome, fn in COLETORES.items():
            if fontes and nome not in fontes:
                continue
            inicio = datetime.now().isoformat(timespec="seconds")
            vistos = novos = 0
            erro = None
            try:
                for ev in fn():
                    vistos += 1
                    try:
                        if processar(ev):
                            novos += 1
                    except Exception as e:
                        print(f"[{nome}] erro no item {ev.get('url')}: {e}")
            except Exception as e:
                erro = f"{type(e).__name__}: {e}"
            database.registrar_execucao(nome, inicio, vistos, novos, erro)
            resumo[nome] = {"vistos": vistos, "novos": novos, "erro": erro}
        return resumo
    finally:
        coleta_lock.release()
