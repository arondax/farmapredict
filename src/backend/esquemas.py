"""Modelos de respuesta de la API (el contrato de docs/ejemplos_endpoints.txt)."""
from datetime import date

from pydantic import BaseModel


class Salud(BaseModel):
    status: str
    datos: dict[str, date]
    modelo_disponible: bool


class ResultadoBusqueda(BaseModel):
    cn: str
    nombre: str | None
    laboratorio: str | None
    comercializado: bool
    problema_activo: bool


class DCP(BaseModel):
    id: str | None
    nombre: str | None


class ProblemaSuministro(BaseModel):
    tipo: int | None
    descripcion: str
    fecha_inicio: date | None
    fecha_fin_prevista: date | None
    observaciones: str | None


class Ficha(BaseModel):
    cn: str
    nregistro: str | None
    nombre: str | None
    laboratorio: str | None
    dcp: DCP
    principio_activo: str | None
    comercializado: bool
    problema_suministro: ProblemaSuministro | None


class Opcion(BaseModel):
    cn: str
    nombre: str | None
    laboratorio: str | None
    dcp: str | None


class Sustitutos(BaseModel):
    cn: str
    dcp: DCP
    vias: list[str]
    sustitutos: list[Opcion]
    criterio_sustitutos: str
    alternativas: list[Opcion]
    criterio_alternativas: str


class Riesgo(BaseModel):
    cn: str
    riesgo: float
    nivel: str
    horizonte_dias: int
    modelo: str
    fecha_calculo: date