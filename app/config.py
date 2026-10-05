import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PDF_DIR = DATA_DIR / "editais"
DB_PATH = DATA_DIR / "concurso.db"

UA = "Mozilla/5.0 (compatible; RadarConcursos/0.1; monitor pessoal de concursos publicos)"
TIMEOUT = 45

# Agendamento da coleta automatica
EM_VERCEL = os.environ.get("VERCEL") == "1"
if EM_VERCEL:
    INTERVALO_HORAS = 0.0  # serverless nao tem agendador: a coleta roda no GitHub Actions
else:
    INTERVALO_HORAS = float(os.environ.get("CONCURSO_INTERVALO_HORAS", "3"))
COLETAR_AO_INICIAR = os.environ.get("CONCURSO_COLLECT_ON_START", "0") == "1"

# Janela de dias que cada fonte olha para tras (deteccao de recem-postados)
DIAS_JANELA_DOU = 3
DIAS_JANELA_QD = 3
DIAS_JANELA_NEWS = 2
MAX_GAZETES_QD = 80
