"""Punto de entrada de la API. -> python -m uvicorn src.backend.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.backend import datos
from src.backend.rutas import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    datos.cargar_presentaciones()
    datos.cargar_problemas_activos()
    datos.indice_por_dcp()
    datos.cargar_vias()
    yield


app = FastAPI(
    title="FarmaPredict API",
    version="0.3.0",
    description="Riesgo de desabastecimiento y sustitutos de medicamentos (datos de AEMPS CIMA).",
    lifespan=lifespan,
)
app.include_router(router)