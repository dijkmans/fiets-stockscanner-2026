# =========================================================
# STOCKTELLING APP – STREAMLIT + SUPABASE + GOOGLE OCR
# Definitieve versie (base64 secrets)
# =========================================================

import io
import re
import json
import base64
from datetime import datetime

import streamlit as st
import pandas as pd

from supabase import create_client, Client
from google.cloud import vision
from google.oauth2 import service_account


# =========================================================
# 1. PAGINA CONFIG
# =========================================================
st.set_page_config(
    page_title="Stocktelling",
    layout="wide"
)
st.title("🚲 Stocktelling")


# =========================================================
# 2. SECRETS CONTROLE
# =========================================================
if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
    st.error("Supabase secrets ontbreken")
    st.stop()

if "GOOGLE_CREDENTIALS_BASE64" not in st.secrets:
    st.error("Google OCR secrets ontbreken")
    st.stop()


# =========================================================
# 3. SUPABASE CONNECTIE
# =========================================================
try:
    supabase: Client = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )
except Exception as e:
    st.error("Supabase verbinding mislukt")
    st.write(e)
    st.stop()


# =========================================================
# 4. GOOGLE OCR INITIALISATIE (BASE64)
# =========================================================
try:
    creds_json = base64.b64decode(
        st.secrets["GOOGLE_CREDENTIALS_BASE64"]
    ).decode("utf-8")

    credentials_info = json.loads(creds_json)

    credentials = service_account.Credentials.from_service_account_info(
        credentials_info
    )

    ocr_client = vision.ImageAnnotatorClient(credentials=credentials)

except Exception as e:
    st.error("Google OCR initialisatie mislukt")
    st.write(e)
    st.stop()


# =========================================================
# 5. OCR FUNCTIE
# =========================================================
def lees_fietsnummer(image_bytes: bytes) -> str | None:
    image = vision.Image(content=image_bytes)
    response = ocr_client.text_detection(image=image)

    if response.error.message:
        raise RuntimeError(response.error.message)

    if not response.text_annotations:
        return None

    tekst = response.text_annotations[0].description
    nummers = re.findall(r"\d+", tekst)

    if not nummers:
        return None

    return max(nummers, key=len)


# =========================================================
# 6. INPUT GEGEVENS
# =========================================================
with st.expander("Instellingen", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        filiaal = st.selectbox(
            "Filiaal",
            ["GEEL", "MOL", "HERSELT", "BOCHOLT"]
        )
        scanner = st.text_input("Naam scanner")
    with col2:
        locatie = st.text_input("Locatie (rek, rij, box)")


# =========================================================
# 7. SCAN
# =========================================================
st.header("📸 Scan fiets")

foto = st.camera_input("Maak foto van fietsnummer")

if foto:
    try:
        fietsnummer = lees_fietsnummer(foto.getvalue())

        if not fietsnummer:
            st.warning("Geen fietsnummer herkend")
        else:
            st.success(f"Herkenning: {fietsnummer}")

            res = supabase.table("stock") \
                .select("*") \
                .eq("fietsnummer", fietsnummer) \
                .execute()

            if res.data:
                st.info("Fiets gevonden in stock")

                if st.button("✅ Scan opslaan"):
                    supabase.table("stock").update({
                        "gescand": True,
                        "gescand_op": datetime.utcnow().isoformat(),
                        "gescand_door": scanner,
                        "filiaal": filiaal,
                        "locatie": locatie
                    }).eq("fietsnummer", fietsnummer).execute()

                    st.success("Scan opgeslagen")

            else:
                st.error("Fietsnummer niet gevonden in stock")

    except Exception as e:
        st.error("OCR fout")
        st.write(e)


# =========================================================
# 8. OVERZICHT
# =========================================================
st.header("📊 Overzicht")

try:
    data = supabase.table("stock").select("*").execute().data
    df = pd.DataFrame(data)

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nog geen data")

except Exception as e:
    st.error("Kon stock niet laden")
    st.write(e)


# =========================================================
# 9. EXCEL EXPORT
# =========================================================
st.header("⬇️ Export")

if not df.empty:
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        "Download Excel",
        buffer,
        file_name="stocktelling.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
