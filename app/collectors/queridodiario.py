"""Querido Diario (Open Knowledge Brasil): diarios oficiais municipais."""
import re
from datetime import date, timedelta

import requests

from ..classify import normalizar
from ..config import DIAS_JANELA_QD, MAX_GAZETES_QD, TIMEOUT, UA
from .base import evento, get_texto, pausar

API = "https://api.queridodiario.org.br/gazettes"

PADRAO_CONCURSO = re.compile(
    r"concurso publico|edital de (abertura de )?concurso|realiza(cao|çao)? de concurso"
    r"|abertura de concurso|concurso publico para|processo seletivo publico", re.I,
)
PADRAO_FORTE = re.compile(
    r"edital de abertura|abertura de concurso|realizacao de concurso|autoriza"
    r"|inscricoes? (abertas|para o|de \d{2}/)|concurso publico para preenchimento"
    r"|concurso publico de provas", re.I,
)
CABECALHO = re.compile(r"concursos? publicos?[/ ]*processos? seletivos?(\s*\d+)?")

# frases que sao sobre concursos ANTIGOS/encerrados, nao sobre edital novo
PADRAO_ANTIGO = re.compile(
    r"convoca|homologa|gabarito|resultado|nomeacao|posse|classifica|recurso administrativo"
    r"|prorrog[oa]", re.I,
)


def trechos_de_concurso(texto: str) -> list:
    fortes, fracos = [], []
    for frase in re.split(r"[.;\n]", texto or ""):
        f = frase.strip()
        if len(f) < 40 or "concurso" not in f.lower():
            continue
        fn = normalizar(f)
        if not PADRAO_CONCURSO.search(fn) or CABECALHO.fullmatch(fn):
            continue
        if len(fortes) < 6 and PADRAO_FORTE.search(fn):
            fortes.append(f[:600])
        elif len(fracos) < 3 and not PADRAO_ANTIGO.search(fn):
            fracos.append(f[:600])
        if len(fortes) >= 6 and len(fracos) >= 3:
            break
    return fortes + fracos


def extrair_orgao(texto: str):
    m = re.search(r"Prefeitura(?: Municipal)? de ([A-ZÀ-Ú][\wÀ-ú'’\- ]+?)(?:[,.;\-–—]|\s+e\s)", texto)
    if m:
        return "Prefeitura de " + m.group(1).strip()
    m = re.search(r"C[âa]mara(?: Municipal)? de ([A-ZÀ-Ú][\wÀ-ú'’\- ]+?)(?:[,.;\-–—]|\s+e\s)", texto)
    if m:
        return "Câmara Municipal de " + m.group(1).strip()
    return None


def coletar(dias: int = DIAS_JANELA_QD):
    desde = (date.today() - timedelta(days=dias)).isoformat()
    offset, processados = 0, 0
    while processados < MAX_GAZETES_QD:
        try:
            r = requests.get(
                API,
                params={"keywords": "concurso", "published_since": desde,
                        "size": 50, "offset": offset},
                headers={"User-Agent": UA}, timeout=90,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"[queridodiario] falha na busca: {e}")
            return
        dados = r.json()
        gazettes = dados.get("gazettes") or []
        if not gazettes:
            return
        for g in gazettes:
            processados += 1
            txt_url = g.get("txt_url")
            if not txt_url:
                continue
            texto = get_texto(txt_url)
            recortes = trechos_de_concurso(texto) if texto else []
            if not recortes:
                continue
            municipio = g.get("territory_name")
            uf = g.get("state_code")
            uniao_recortes = " ... ".join(recortes)
            orgao = extrair_orgao(uniao_recortes) or f"Município de {municipio}"
            yield evento(
                fonte="queridodiario",
                fonte_nome=f"Diário oficial de {municipio}-{uf}",
                url=txt_url,
                fonte_url=g.get("url"),
                pdf_url=g.get("url"),
                titulo=f"Concurso público — {municipio}/{uf}",
                orgao=orgao,
                texto=uniao_recortes[:8000],
                uf=uf,
                municipio=municipio,
                nivel="municipal",
                data_publicacao=g.get("date"),
            )
            pausar(0.8)
        offset += len(gazettes)
        if offset >= (dados.get("total_gazettes") or 0) or processados >= MAX_GAZETES_QD:
            return
