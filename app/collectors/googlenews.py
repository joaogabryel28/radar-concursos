"""Google Noticias: detector generico de anuncios (editais novos e concursos previstos)."""
import re
import xml.etree.ElementTree as ET

import requests

from ..config import DIAS_JANELA_NEWS, TIMEOUT, UA
from .base import evento, pausar

RSS = "https://news.google.com/rss/search"
CONSULTAS = [
    '"concurso público" edital when:2d',
    '"concurso" "inscrições abertas" when:2d',
    '"concurso" autorizado when:3d',
]


def _data_iso(pubdate: str):
    try:
        from email.utils import parsedate_to_datetime
        if not pubdate:
            return None
        return parsedate_to_datetime(pubdate).date().isoformat()
    except Exception:
        return None


def _orgao_de_manchete(titulo: str):
    m = re.search(r"[Pp]refeitura (?:Municipal )?de ([A-ZÀ-Ú][\wÀ-ú'’\- ]+?)(?:[-–—,.;:]|\sabre|\sabre\s)", titulo)
    if m:
        return "Prefeitura de " + m.group(1).strip()
    m = re.search(r"[Cc][âa]mara [Mm]unicipal de ([A-ZÀ-Ú][\wÀ-ú'’\- ]+?)(?:[-–—,.;:]|$)", titulo)
    if m:
        return "Câmara Municipal de " + m.group(1).strip()
    m = re.search(r"\b(TRT|TJ|TRF|TRE|TCE|TCM|MPE|DPE)\s*-?\s*(\d{1,2}|[A-Z]{2})\b", titulo)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"Pol[íi]cia (?:Militar|Civil) (?:de |do |da )?([A-ZÀ-Ú][\wÀ-ú ]{3,30})", titulo)
    if m:
        return "Polícia " + m.group(1).strip()
    return None


def coletar():
    vistos = set()
    for consulta in CONSULTAS:
        try:
            r = requests.get(
                RSS,
                params={"q": consulta, "hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"},
                headers={"User-Agent": UA}, timeout=TIMEOUT,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"[googlenews] falha em '{consulta}': {e}")
            continue
        try:
            raiz = ET.fromstring(r.content)
        except ET.ParseError:
            continue
        for item in raiz.iter("item"):
            titulo = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            if not titulo or not link or link in vistos:
                continue
            vistos.add(link)
            fonte = (item.findtext("source") or "").strip()
            titulo_limpo = titulo
            if fonte and titulo_limpo.endswith(fonte):
                titulo_limpo = titulo_limpo[: -len(fonte)].strip(" -–—")
            else:
                titulo_limpo = re.sub(r"\s*-\s*[^-]{2,60}$", "", titulo).strip()
            yield evento(
                fonte="googlenews",
                fonte_nome=f"Notícias ({fonte or 'Google Notícias'})",
                url=link,
                fonte_url=link,
                titulo=titulo_limpo,
                orgao=_orgao_de_manchete(titulo_limpo),
                texto=titulo_limpo,
                data_publicacao=_data_iso(item.findtext("pubDate")),
                status_padrao="previsto",
            )
        pausar(2)
