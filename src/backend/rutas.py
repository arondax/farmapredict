"""Endpoints HTTP. Solo traducen entre HTTP y servicios: sin lógica de negocio."""
from fastapi import APIRouter, HTTPException, Query

from src.backend import datos, servicios
from src.backend.esquemas import Ficha, ResultadoBusqueda, Riesgo, Salud, Sustitutos

router = APIRouter()


@router.get("/health", response_model=Salud)
def health():
    return {
        "status": "ok",
        "datos": datos.fechas_datos(),
        "modelo_disponible": datos.cargar_riesgo() is not None,
    }


@router.get("/medicamentos", response_model=list[ResultadoBusqueda])
def buscar(q: str = Query(..., min_length=3), limite: int = Query(20, ge=1, le=100)):
    return servicios.buscar(q, limite)


@router.get("/medicamentos/{cn}", response_model=Ficha)
def ficha(cn: str):
    resultado = servicios.ficha(cn)
    if resultado is None:
        raise HTTPException(status_code=404, detail="CN no encontrado")
    return resultado


@router.get("/medicamentos/{cn}/sustitutos", response_model=Sustitutos)
def sustitutos(cn: str):
    resultado = servicios.sustitutos(cn)
    if resultado is None:
        raise HTTPException(status_code=404, detail="CN no encontrado")
    return resultado


@router.get("/medicamentos/{cn}/riesgo", response_model=Riesgo)
def riesgo(cn: str):
    if cn not in datos.cargar_presentaciones():
        raise HTTPException(status_code=404, detail="CN no encontrado")
    try:
        resultado = servicios.riesgo(cn)
    except servicios.ModeloNoDisponible:
        raise HTTPException(status_code=503, detail="Modelo de riesgo no disponible todavía")
    if resultado is None:
        raise HTTPException(status_code=404, detail="Sin predicción de riesgo para este CN")
    return resultado