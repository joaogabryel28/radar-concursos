import os

import requests
from fastapi import APIRouter, HTTPException, Query

from .. import database
from ..classify import AREAS, CURSOS
from ..config import EM_VERCEL
from ..ingest import rodar_coleta

router = APIRouter(prefix="/api")


@router.get("/concursos")
def api_concursos(
    aba: str = Query("abertas", pattern="^(abertas|publicados|previstos|todos)$"),
    uf: str = None,
    area: str = None,
    curso: str = None,
    nivel: str = None,
    q: str = None,
    novos: int = None,
    limite: int = Query(200, ge=1, le=500),
):
    itens = database.listar_concursos(
        aba=aba, uf=uf, area=area, curso=curso, nivel=nivel,
        q=q, novos_dias=novos, limite=limite,
    )
    return {"total": len(itens), "itens": itens}


@router.get("/concursos/{id_}")
def api_concurso(id_: int):
    item = database.obter_concurso(id_)
    if item is None:
        raise HTTPException(404, "concurso não encontrado")
    return item


@router.get("/meta")
def api_meta():
    return {
        **database.meta(),
        "areas": sorted(AREAS),
        "cursos": sorted(CURSOS),
    }


@router.post("/coletar")
def api_coletar(fontes: str = None):
    if EM_VERCEL:
        repo = os.environ.get("GITHUB_REPO")
        token = os.environ.get("GITHUB_DISPATCH_TOKEN")
        if not (repo and token):
            return {
                "disparado": False,
                "mensagem": "Neste deploy a coleta roda no GitHub Actions a cada 3 horas. "
                "Para o botao coletar na hora, configure GITHUB_REPO e GITHUB_DISPATCH_TOKEN na Vercel.",
            }
        r = requests.post(
            f"https://api.github.com/repos/{repo}/dispatches",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            json={"event_type": "coleta-manual"},
            timeout=10,
        )
        if r.status_code == 204:
            return {"disparado": True, "mensagem": "Coleta disparada no GitHub Actions — recarregue a pagina em 2-3 minutos."}
        return {"disparado": False, "mensagem": f"Falha ao disparar a coleta: HTTP {r.status_code}"}
    lista = [f.strip() for f in fontes.split(",")] if fontes else None
    return rodar_coleta(lista)
