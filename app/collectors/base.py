"""Utilidades comuns aos coletores."""
import time

import requests
from bs4 import BeautifulSoup

from ..config import TIMEOUT, UA


def http_get(url: str, timeout: int = TIMEOUT):
    r = requests.get(
        url,
        headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"},
        timeout=timeout,
    )
    return r.status_code, r.content


def get_sopa(url: str, from_encoding: str = None, timeout: int = TIMEOUT):
    cod, conteudo = http_get(url, timeout)
    if cod != 200:
        return None
    if from_encoding:
        return BeautifulSoup(conteudo, "lxml", from_encoding=from_encoding)
    return BeautifulSoup(conteudo, "lxml")


def get_texto(url: str, encoding: str = "utf-8", timeout: int = TIMEOUT, limite: int = 1_200_000):
    cod, conteudo = http_get(url, timeout)
    if cod != 200:
        return None
    return conteudo[:limite].decode(encoding, errors="replace")


def evento(**kwargs) -> dict:
    """Evento padronizado. Campos: fonte, fonte_nome, url, fonte_url, titulo,
    orgao, texto, uf, municipio, banca, data_publicacao, pdf_url, edital_url,
    inscricoes_url, nivel, status_padrao."""
    base = {
        "fonte": None, "fonte_nome": None, "url": None, "fonte_url": None,
        "titulo": "", "orgao": None, "texto": "", "uf": None, "municipio": None,
        "banca": None, "data_publicacao": None, "pdf_url": None, "edital_url": None,
        "inscricoes_url": None, "nivel": None, "status_padrao": "edital_publicado",
    }
    base.update(kwargs)
    return base


def pausar(segundos: float = 1.5):
    time.sleep(segundos)
