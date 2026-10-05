"""IBFC: lista de concursos via plataforma selecao.net.br."""
import re

from .base import evento, get_sopa

BASE = "https://ibfc.selecao.net.br"
PAGINAS = [
    (f"{BASE}/index/abertos/", "inscricoes_abertas"),
    (f"{BASE}/index/1/", "edital_publicado"),
]


def _nome_do_concurso(a) -> str:
    sp = a.select_one(".texto_cliente") or a.select_one("h5") or a.select_one("h4")
    nome = sp.get_text(" ", strip=True) if sp else a.get_text(" ", strip=True)
    nome = re.sub(r"\s+", " ", nome)
    nome = re.sub(r"^(Inscrições Abertas|Em andamento|Finalizado|Detalhes)\s*", "", nome, flags=re.I)
    return nome.strip(" -–—")


def coletar():
    for pagina, status in PAGINAS:
        sopa = get_sopa(pagina, from_encoding="cp1252")
        if sopa is None:
            print(f"[ibfc] nao conseguiu carregar {pagina}")
            continue
        for a in sopa.select("a.lista-concurso"):
            href = a.get("href") or ""
            if not re.match(r"^/informacoes/\d+/", href):
                continue
            nome = _nome_do_concurso(a)
            if len(nome) < 6:
                continue
            yield evento(
                fonte="ibfc",
                fonte_nome="IBFC",
                url=BASE + href,
                fonte_url=pagina,
                edital_url=BASE + href,
                titulo=nome,
                orgao=nome,
                texto=nome + " — concurso público com edital publicado",
                banca="IBFC",
                status_padrao=status,
            )
