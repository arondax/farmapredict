# src/cima/models.py
from pydantic import BaseModel, ConfigDict


class CimaBase(BaseModel):
    model_config = ConfigDict(extra="ignore")


# --- Objetos anidados ---

class Item(CimaBase):
    """Objeto genérico id/nombre (forma farmacéutica, vía, VTM...)."""
    id: int | None = None
    nombre: str | None = None


class Estado(CimaBase):
    # Fechas en epoch en milisegundos
    aut: int | None = None    # autorización
    susp: int | None = None   # suspensión
    rev: int | None = None    # revocación


class Documento(CimaBase):
    tipo: int                 # 1 = ficha técnica, 2 = prospecto, ...
    url: str | None = None
    urlHtml: str | None = None
    secc: bool | None = None
    fecha: int | None = None


class Foto(CimaBase):
    tipo: str | None = None   # materialas / formafarmac
    url: str | None = None
    fecha: int | None = None


# --- Medicamento ---

class Medicamento(CimaBase):
    nregistro: str
    nombre: str
    pactivos: str | None = None          # principios activos concatenados
    labtitular: str | None = None
    cpresc: str | None = None            # condiciones de prescripción
    estado: Estado | None = None
    dosis: str | None = None

    comerc: bool | None = None
    receta: bool | None = None
    generico: bool | None = None
    conduc: bool | None = None           # afecta a la conducción
    triangulo: bool | None = None
    huerfano: bool | None = None
    biosimilar: bool | None = None
    psum: bool | None = None             # problemas de suministro
    ema: bool | None = None              # autorizado por procedimiento centralizado
    notas: bool | None = None
    materialesInf: bool | None = None

    nosustituible: Item | None = None
    formaFarmaceutica: Item | None = None
    formaFarmaceuticaSimplificada: Item | None = None
    vtm: Item | None = None
    viasAdministracion: list[Item] = []

    docs: list[Documento] = []
    fotos: list[Foto] = []


# --- Respuesta paginada ---

class MedicamentosResponse(CimaBase):
    totalFilas: int
    pagina: int
    tamanioPagina: int
    resultados: list[Medicamento]