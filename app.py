import streamlit as st
import requests
import re
import openai
import json

# ==============================
#  Funciones auxiliares
# ==============================

def extract_ids_from_url(url):
    """
    Extrae groupId y reportId de un link de Power BI.
    Ejemplo: https://app.powerbi.com/groups/{groupId}/reports/{reportId}
    """
    group_match = re.search(r'/groups/([a-f0-9-]+)/', url)
    report_match = re.search(r'/reports/([a-f0-9-]+)', url)
    group_id = group_match.group(1) if group_match else None
    report_id = report_match.group(1) if report_match else None
    return group_id, report_id


def get_report_metadata(access_token, group_id, report_id):
    """
    Obtiene metadatos de un reporte en Power BI.
    """
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{group_id}/reports/{report_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error al obtener reporte: {response.status_code} {response.text}")
        return None


def get_datasets(access_token, group_id):
    """
    Lista datasets de un grupo.
    """
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{group_id}/datasets"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("value", [])
    return []


def generate_gpt_report(openai_api_key, metadata, datasets):
    """
    Usa GPT para redactar un informe ejecutivo con los metadatos del dashboard.
    """
    openai.api_key = openai_api_key

    prompt = f"""
Eres un analista de medios senior.
Genera un informe ejecutivo a partir de la siguiente metadata de un dashboard de Power BI.

METADATA DEL REPORTE:
{json.dumps(metadata, indent=2)}

DATASETS VINCULADOS:
{json.dumps(datasets, indent=2)}

Redacta el informe con este formato:
1. **Resumen ejecutivo**
2. **Estructura del reporte** (qué páginas contiene y para qué sirven)
3. **Conexión de datos** (datasets vinculados y su posible relevancia)
4. **Recomendaciones para gerencia**
Usa un tono profesional, claro y orientado a negocio.
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # puedes usar gpt-4o si tu cuenta lo soporta
        messages=[{"role": "system", "content": "Eres un analista experto en medios y dashboards."},
                  {"role": "user", "content": prompt}],
        temperature=0.7,
    )

    return response.choices[0].message["content"]


# ==============================
#  Interfaz Streamlit
# ==============================

st.title("📊 Power BI → Informe Ejecutivo con GPT")

st.write("Pega el link del dashboard/report de Power BI y obtén un informe detallado.")

access_token = st.text_input("🔑 Access Token de Power BI", type="password")
gpt_api_key = st.text_input("🔑 API Key de OpenAI", type="password")
report_url = st.text_input("📎 Link del Report/Dashboard de Power BI")

if st.button("Generar Informe"):
    if not access_token or not gpt_api_key or not report_url:
        st.error("⚠️ Debes ingresar Access Token, API Key de GPT y el link del dashboard.")
    else:
        group_id, report_id = extract_ids_from_url(report_url)
        if not group_id or not report_id:
            st.error("⚠️ No se pudo extraer groupId/reportId del link. Revisa el formato.")
        else:
            metadata = get_report_metadata(access_token, group_id, report_id)
            datasets = get_datasets(access_token, group_id)

            if metadata:
                report = generate_gpt_report(gpt_api_key, metadata, datasets)
                st.subheader("📑 Informe Ejecutivo")
                st.markdown(report)
