"""Extracao de campos (vagas, salario, datas) a partir do texto de editais."""
import re
from datetime import datetime

import requests

try:
    import pymupdf
    TEM_PDF = True
except ImportError:
    TEM_PDF = False

from .config import TIMEOUT, UA


def baixar_pdf(url: str):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=90)
        r.raise_for_status()
    except requests.RequestException:
        return None
    conteudo = r.content
    if len(conteudo) > 20_000_000 or not conteudo.startswith(b"%PDF"):
        return None
    return conteudo


def texto_do_pdf(conteudo: bytes):
    if not (TEM_PDF and conteudo):
        return None
    try:
        doc = pymupdf.open(stream=conteudo, filetype="pdf")
        return "\n".join(p.get_text() for p in doc)[:400_000]
    except Exception:
        return None


def _data_iso(s: str):
    try:
        return datetime.strptime(s, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def extrair_campos(texto: str) -> dict:
    """Best-effort: valores maximos plausiveis encontrados no texto do edital."""
    if not texto:
        return {}
    limpo = re.sub(r"\s+", " ", texto)

    vagas = 0
    for m in re.finditer(r"(\d{1,5})\s*(?:\([^)]{0,40}\))?\s*vagas", limpo, re.I):
        v = int(m.group(1))
        if 0 < v <= 30_000:
            vagas = max(vagas, v)
    for m in re.finditer(r"(\d{1,2}(?:[.,]\d)?)\s*mil vagas", limpo, re.I):
        v = int(float(m.group(1).replace(",", ".")) * 1000)
        if 0 < v <= 30_000:
            vagas = max(vagas, v)

    salario = 0.0
    for m in re.finditer(r"R\$\s*([\d.]+(?:,\d{2})?)", limpo):
        try:
            val = float(m.group(1).replace(".", "").replace(",", "."))
        except ValueError:
            continue
        if 600 <= val <= 200_000:
            salario = max(salario, val)

    data_insc = None
    data_prova = None
    for frase in re.split(r"[.;\n]", texto):
        f = frase.lower()
        datas = [_data_iso(m.group(1)) for m in re.finditer(r"(\d{2}/\d{2}/\d{4})", frase)]
        datas = [d for d in datas if d]
        if not datas:
            continue
        if "inscri" in f:
            data_insc = max(data_insc, *datas) if data_insc else max(datas)
        elif "prova" in f and any(p in f for p in ("aplicação", "realização", "objetiva", "data da prova")):
            data_prova = max(data_prova, *datas) if data_prova else max(datas)

    return {
        "vagas": vagas or None,
        "salario_max": salario or None,
        "data_inscricoes": data_insc,
        "data_prova": data_prova,
        "resumo": limpo[:400],
    }
