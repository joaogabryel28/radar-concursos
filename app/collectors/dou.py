"""Diario Oficial da Uniao: busca via portal in.gov.br (JSON embutido na pagina)."""
import json
import re
import time
from datetime import date, timedelta

import requests

from ..config import DIAS_JANELA_DOU, TIMEOUT, UA
from .base import evento, pausar

API = "https://www.in.gov.br/consulta/-/buscar/dou"
BASE_WEB = "https://www.in.gov.br/web/dou/-/"
SECOES = ["DO1", "DO2", "DO3"]
CONSULTAS = ['"concurso público"', '"edital de abertura"', '"realização de concurso"']
SCRIPT_TAG = r'id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params"[^>]*>(.*?)</script>'


def coletar(dias: int = DIAS_JANELA_DOU):
    hoje = date.today()
    payload_base = {
        "exactDate": "personalizado",
        "publishFrom": (hoje - timedelta(days=dias)).strftime("%d-%m-%Y"),
        "publishTo": hoje.strftime("%d-%m-%Y"),
        "sortType": "0",
        "s": SECOES,
    }
    vistos = set()
    for consulta in CONSULTAS:
        try:
            r = requests.get(
                API, params={**payload_base, "q": consulta},
                headers={"User-Agent": UA}, timeout=TIMEOUT,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"[dou] falha em '{consulta}': {e}")
            continue
        m = re.search(SCRIPT_TAG, r.text, re.S)
        if not m:
            continue
        arr = (json.loads(m.group(1)) or {}).get("jsonArray") or []
        for it in arr:
            slug = str(it.get("urlTitle") or "").strip("/")
            if not slug:
                continue
            url = BASE_WEB + slug
            if url in vistos:
                continue
            vistos.add(url)
            hierarquia = str(it.get("hierarchyStr") or "")
            conteudo = re.sub(r"<[^>]+>", " ", str(it.get("content") or ""))
            yield evento(
                fonte="dou",
                fonte_nome="Diário Oficial da União",
                url=url,
                fonte_url=url,
                edital_url=url,
                titulo=re.sub(r"\s+", " ", str(it.get("title") or "")).strip(),
                orgao=hierarquia.split("/")[-1].strip() or None,
                texto=" ".join([str(it.get("title") or ""), conteudo, hierarquia]),
                data_publicacao=it.get("pubDate"),
                art_type=str(it.get("artType") or ""),
            )
        pausar(2)
