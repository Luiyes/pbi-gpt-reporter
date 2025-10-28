import streamlit as st
import requests
import re
import json
import openai
import msal

# ==============================
# Configuración desde Secrets
# ==============================
CLIENT_ID = st.secrets["powerbi"]["client_id"]
TENANT_ID = st.secrets["powerbi"]["tenant_id"]
CLIENT_SECRET = st.secrets["powerbi"].get("client_secret", None)
OPENAI_API_KEY = st.secrets["openai"]["api_key"]

openai.api_key = OPENAI_API_KEY

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]

# ==============================
# Autenticación
# ==============================
def get_token_service_principal():
    """Obtiene un token de acceso usando Service Principal"""
    if not CLIENT_SECRET:
        st.error("❌ No se encontró CLIENT_SECRET en los secrets")
        return None

    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    token = app.acquire_token_for_client(SCOPE)
    return token.get("access_token")


# ==============================
# Funciones de Power BI
# ==============================
def extract_ids_from_url(url):
    """Extrae groupId y reportId desde la URL de Power BI"""
    group_match = re.search(r'/groups/([a-f0-9-]+)/', url)
    report_match = re.search(r'/reports/([a-f0-9-]+)', url)
    group_id = group_match.group(1) if group_match else None
    report_id = report_match.group(1) if report_match else None
    return group_id, report_id


def call_pbi(token, url):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    st.error(f"⚠️ Error {r.status_code} al consultar {url}")
    try:
        st.json(r.json())
    except:
        st.write(r.text)
    return None


def get_report_metadata(token, group_id, report_id):
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{group_id}/reports/{report_id}"
    return call_pbi(token, url)


def get_group_datasets(token, group_id):
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{group_id}/datasets"
    data = call_pbi(token, url) or {}
    return data.get("value", [])


# ==============================
# GPT: Informe ejecutivo
# ==============================
def generate_gpt_report(metadata, datasets):
    prompt = f"""
Eres un analista senior de negocios. A partir de estos metadatos de un reporte de Power BI,
genera un informe ejecutivo con:

1. Resumen ejecutivo
2. Estructura del reporte (páginas y su objetivo)
3. Conexión de datos (datasets y relevancia)
4. Recomendaciones para gerencia

METADATA:
{json.dumps(metadata, indent=2, ensure_ascii=False)}

DATASETS:
{json.dumps(datasets, indent=2, ensure_ascii=False)}
"""

    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un experto en análisis de dashboards."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6,
    )
    return resp.choices[0].message["content"]


# ==============================
# Interfaz Streamlit
# ==============================
st.set_page_config(page_title="PBI GPT Reporter", page_icon="📊", layout="wide")
st.title("📊 Power BI → Informe Ejecutivo con GPT")

st.write("Pega el link del dashboard/report de Power BI y obtén un informe detallado.")

report_url = st.text_input("🔗 Link del Report/Dashboard de Power BI")

if st.button("Generar Informe"):
    if not report_url:
        st.error("Por favor pega un link válido de Power BI")
        st.stop()

    group_id, report_id = extract_ids_from_url(report_url)
    if not group_id or not report_id:
        st.error("❌ No se pudo extraer groupId o reportId de la URL")
        st.stop()

    token = get_token_service_principal()
    if not token:
        st.stop()

    metadata = get_report_metadata(token, group_id, report_id)
    datasets = get_group_datasets(token, group_id)

    if metadata:
        st.subheader("🗂️ Metadatos del Reporte")
        st.json(metadata)

        st.subheader("🧩 Datasets conectados")
        st.json(datasets)

        st.subheader("🧾 Informe ejecutivo (GPT)")
        try:
            informe = generate_gpt_report(metadata, datasets)
            st.markdown(informe)
        except Exception as e:
            st.error(f"Error al generar informe con GPT: {e}")
