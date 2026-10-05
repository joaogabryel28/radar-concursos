from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import database
from .config import BASE_DIR, COLETAR_AO_INICIAR, EM_VERCEL, INTERVALO_HORAS
from .ingest import rodar_coleta
from .web.routes import router

STATIC_DIR = BASE_DIR / "app" / "web" / "static"
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not EM_VERCEL:
        database.init_db()
    if INTERVALO_HORAS > 0:
        kwargs = {"next_run_time": datetime.now() + timedelta(seconds=15)} if COLETAR_AO_INICIAR else {}
        scheduler.add_job(rodar_coleta, "interval", hours=INTERVALO_HORAS, id="coleta", **kwargs)
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Radar Concursos", lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")
