"""Front Streamlit de FarmaPredict. Ejecutar: python -m streamlit run src/frontend/app.py"""
import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="FarmaPredict", layout="wide")
st.title("FarmaPredict")
st.caption("Riesgo de desabastecimiento y sustitutos. Información de apoyo: la decisión es del farmacéutico.")


def get(ruta, **params):
    try:
        return requests.get(f"{API_URL}{ruta}", params=params, timeout=15)
    except requests.RequestException:
        st.error("No se puede conectar con la API. ¿Está arrancada?")
        st.stop()


with st.sidebar:
    r = get("/health")
    if r.ok:
        d = r.json()
        st.success("API activa")
        st.write("Datos:", d["datos"])
        st.write("Modelo de riesgo:", "disponible" if d["modelo_disponible"] else "no disponible")

q = st.text_input("Buscar medicamento (mínimo 3 letras)")
if len(q) >= 3:
    r = get("/medicamentos", q=q, limite=20)
    resultados = r.json() if r.ok else []
    if not resultados:
        st.info("Sin resultados.")
    else:
        etiquetas = {
            f'{m["nombre"][:90]} (CN {m["cn"]})' + (" ⚠ problema de suministro" if m["problema_activo"] else ""): m["cn"]
            for m in resultados
        }
        cn = etiquetas[st.selectbox("Resultados", list(etiquetas))]

        tab1, tab2, tab3 = st.tabs(["Ficha", "Sustitutos", "Riesgo"])

        with tab1:
            ficha = get(f"/medicamentos/{cn}").json()
            st.subheader(ficha["nombre"])
            st.write(f'**Laboratorio:** {ficha["laboratorio"]}')
            st.write(f'**Principio activo:** {ficha["principio_activo"]}')
            st.write(f'**DCP:** {ficha["dcp"]["nombre"]}')
            st.write(f'**Comercializado:** {"Sí" if ficha["comercializado"] else "No"}')
            p = ficha["problema_suministro"]
            if p:
                st.error(f'Problema de suministro (tipo {p["tipo"]}): {p["descripcion"]}. '
                         f'Desde {p["fecha_inicio"]}. Fin previsto: {p["fecha_fin_prevista"] or "sin fecha"}.')
            else:
                st.success("Sin problema de suministro activo.")

        with tab2:
            s = get(f"/medicamentos/{cn}/sustitutos").json()
            st.markdown("#### Sustitutos equivalentes")
            st.caption(s["criterio_sustitutos"])
            if s["sustitutos"]:
                st.dataframe(s["sustitutos"], use_container_width=True)
            else:
                st.info("No hay equivalentes disponibles.")
            st.markdown("#### Alternativas a valorar")
            st.warning("Otra dosis o forma: requieren valoración del farmacéutico o del médico.")
            if s["alternativas"]:
                st.dataframe(s["alternativas"], use_container_width=True)
            else:
                st.info("No hay alternativas.")

        with tab3:
            r = get(f"/medicamentos/{cn}/riesgo")
            if r.status_code == 200:
                j = r.json()
                st.metric("Riesgo a 30 días", f'{j["riesgo"]:.1%}')
                st.write(f'**Nivel:** {j["nivel"].upper()}')
                st.caption(f'Modelo {j["modelo"]} · calculado el {j["fecha_calculo"]}. '
                           "Es una ayuda a la decisión, no una certeza.")
            elif r.status_code == 503:
                st.info("El modelo de riesgo todavía no está disponible.")
            elif r.status_code == 404:
                st.info("Sin predicción para este medicamento (por ejemplo, si ya tiene un problema de suministro activo).")
            else:
                st.error(f"Error {r.status_code}")