"""Fundacao Carlos Chagas (FCC): lista de concursos ativos."""
import re

from .base import evento, get_sopa

LISTA = "https://www.concursosfcc.com.br/"
PADRAO_LINK = re.compile(
    r"^(?:https?://www\.concursosfcc\.com\.br)?/concursos/[a-z0-9]+/index\.html$", re.I
)


def coletar():
    sopa = get_sopa(LISTA, from_encoding="cp1252")
    if sopa is None:
        print("[fcc] nao conseguiu carregar a listagem")
        return
    for a in sopa.select('a[href*="/concursos/"]'):
        href = a.get("href") or ""
        if not PADRAO_LINK.match(href):
            continue
        url = href if href.startswith("http") else "https://www.concursosfcc.com.br" + href
        nome = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()
        if len(nome) < 6:
            continue
        yield evento(
            fonte="fcc",
            fonte_nome="Fundação Carlos Chagas (FCC)",
            url=url,
            fonte_url=LISTA,
            edital_url=url,
            titulo=nome,
            orgao=nome,
            texto=nome + " — concurso público com edital publicado e inscrições abertas",
            banca="FCC",
        )
