"""
Backfill del último episodio de suministro de cada CN del catálogo.
Reanudable: si se corta, se vuelve a lanzar y continúa con los CN pendientes.

python -m src.backfill_psuministro --limite 200    # prueba para medir velocidad
python -m src.backfill_psuministro                 # completo
"""
import argparse
import glob
import json
import os
import time
from datetime import datetime

import requests

from src.api.api import get_psuministro_cn_raw
from src.config import DATA_RAW_DIR

CARPETA = os.path.join(DATA_RAW_DIR, "cima")
RUTA_SALIDA = os.path.join(CARPETA, "backfill_psuministro.jsonl")


def _cns_catalogo() -> list[str]:
    """CN del último snapshot de /presentaciones, como string (formato de origen)."""
    archivos = sorted(glob.glob(os.path.join(CARPETA, "presentaciones_*.json")))
    if not archivos:
        raise FileNotFoundError("No hay snapshot de presentaciones: python -m src.snapshot_diario presentaciones")
    with open(archivos[-1], encoding="utf-8") as f:
        registros = json.load(f)
    print(f"Catálogo: {os.path.basename(archivos[-1])}")
    return sorted({str(r["cn"]) for r in registros if r.get("cn")})


def _ya_consultados() -> set[str]:
    """CN que ya están en el fichero de salida (para reanudar)."""
    if not os.path.exists(RUTA_SALIDA):
        return set()
    with open(RUTA_SALIDA, encoding="utf-8") as f:
        return {json.loads(linea)["cn"] for linea in f if linea.strip()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pausa", type=float, default=0.2, help="segundos entre peticiones")
    parser.add_argument("--limite", type=int, default=None, help="máximo de CN en esta ejecución")
    args = parser.parse_args()

    cns = _cns_catalogo()
    hechos = _ya_consultados()
    pendientes = [cn for cn in cns if cn not in hechos][: args.limite]
    print(f"CN en catálogo: {len(cns)} | ya consultados: {len(hechos)} | en esta ejecución: {len(pendientes)}")

    inicio = time.perf_counter()
    con_episodio = errores = 0

    with open(RUTA_SALIDA, "a", encoding="utf-8") as f:
        for i, cn in enumerate(pendientes, 1):
            try:
                respuesta = get_psuministro_cn_raw(cn)
            except requests.RequestException as e:
                # No se escribe: queda pendiente y se reintenta en la siguiente ejecución
                errores += 1
                print(f"ERROR {cn}: {e}")
                continue

            linea = {
                "cn": cn,  # clave: el CN consultado (string), no el de la respuesta (viene como int)
                "consultado": datetime.now().isoformat(timespec="seconds"),
                "respuesta": respuesta,
            }
            f.write(json.dumps(linea, ensure_ascii=False) + "\n")
            f.flush()  # si se corta, lo ya escrito no se pierde
            con_episodio += "fini" in respuesta

            if i % 500 == 0 or i == len(pendientes):
                ritmo = i / (time.perf_counter() - inicio)
                restante_h = (len(pendientes) - i) / ritmo / 3600
                print(f"{i}/{len(pendientes)} | con episodio: {con_episodio} | errores: {errores} "
                      f"| {ritmo:.1f} CN/s | quedan ~{restante_h:.1f} h")
            time.sleep(args.pausa)


if __name__ == "__main__":
    main()