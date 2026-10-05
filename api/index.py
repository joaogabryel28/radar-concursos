"""Entrypoint serverless (Vercel) do Radar Concursos.

O Vercel nao executa o agendador nem grava no banco: ele apenas serve a
interface e a API em modo leitura. A coleta roda no GitHub Actions e o
banco chega atualizado a cada push do workflow (o workflow copia
data/concurso.db para api/data/concurso.db, que e o caminho incluido no
bundle da funcao).

O codigo do app pode chegar ao serverless na raiz do projeto ou dentro
de api/, dependendo de como o builder resolve o includeFiles — por isso
detectamos as duas raizes possiveis aqui.
"""
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
# O builder da plataforma resolve includeFiles relativo a api/: o banco
# que vai para o bundle e a copia em api/data/
os.environ["CONCURSO_DB_PATH"] = str(AQUI / "data" / "concurso.db")

for raiz in (AQUI.parent, AQUI):
    if (raiz / "app" / "main.py").exists():
        if str(raiz) not in sys.path:
            sys.path.insert(0, str(raiz))
        break

from app.main import app  # noqa: E402
