"""Entrypoint serverless (Vercel) do Radar Concursos.

O Vercel nao executa o agendador nem grava no banco: ele apenas serve a
interface e a API em modo leitura. A coleta roda no GitHub Actions e o
banco (data/concurso.db) chega atualizado a cada push do workflow.

O codigo do app e o banco podem chegar ao serverless na raiz do projeto
ou dentro de api/, dependendo de como a Vercel resolve o includeFiles —
por isso detectamos as duas raizes possiveis aqui.
"""
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
for raiz in (AQUI.parent, AQUI):
    if (raiz / "app" / "main.py").exists():
        if str(raiz) not in sys.path:
            sys.path.insert(0, str(raiz))
        break

from app.main import app  # noqa: E402

# Diagnostico temporario: mostra o que o runtime entrega ao ASGI.
@app.api_route("/{caminho:path}", methods=["GET", "POST"], include_in_schema=False)
async def _diagnostico_caminho(request, caminho: str):
    return {
        "rota_coringa_recebida": caminho,
        "scope_path": request.scope.get("path"),
        "root_path": request.scope.get("root_path"),
        "x_matched_path": request.headers.get("x-matched-path"),
        "x_forwarded": request.headers.get("x-forwarded-uri")
        or request.headers.get("x-forwarded-path"),
        "url": str(request.url),
    }
