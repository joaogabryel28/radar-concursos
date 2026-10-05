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
