"""Entrypoint serverless (Vercel) do Radar Concursos.

O Vercel nao executa o agendador nem grava no banco: ele apenas serve a
interface e a API em modo leitura. A coleta roda no GitHub Actions e o
banco (data/concurso.db) chega atualizado a cada push do workflow.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.main import app  # noqa: E402
