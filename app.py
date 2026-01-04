# =========================================================
# STOCKTELLING PRO – MET GOOGLE OCR
# =========================================================

import os
import io
import re
import time
from datetime import datetime

import streamlit as st
import pandas as pd
from supabase import create_client, Client
from google.cloud import vision


# =========================================================
# 0. GOOGLE OCR CONFIGURATIE
# =========================================================
# JSON key moet in dezelfde map staan als app.py
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "fiets-scanner-key.json"


# =========================================================
# 1. PAGINA INSTELLINGEN
# =========================================================
st.set_page_config(
    page_title="Stocktelling Pro",
    layout="wide",
    initial_sidebar_state="collapsed"
)
st.title("🚲 Stocktelling + Controle")


# =========================================================
# 2. SUPABASE CONNECTIE
# =========================================================
SUPABASE_URL = "https://ubgyxilkcmzvtpxresos.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InViZ3l4aWxrY216dnRweHJlc29zIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzQzOTM1NiwiZXhwIjoyMDgzMDE1MzU2fQ.EhllRUxKxjcXFt3bSbiV0gs2v9LNLvn6aOeVkkZFviY"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"❌ Database fout: {e}")
    st.stop()


# =========================================================
# 3. SESSION STATE
# =========================================================
if "scan_result" not in st.session_state:
    st.session_state.scan_result = None

if "unknown_items" not in st.session_state:
    st.session_state.unknown_items = []

if "success_msg" not in st.session_state:
    st.session_state.success_msg = None

if "input_field" not in st.session_state:
    st.session_state.input_field = ""


# =========================================================
# 4. INSTELLINGEN
# =========================================================
with st.expander("⚙️ Instellingen", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        filiaal = st.selectbox("Filiaal", ["GEEL", "MOL", "HERSELT", "BOCHOLT"])
        scanner_naam = st.text_input("Jouw naam", value="Piet")
    with col2:
        locatie = st.text_input("Locatie (bv. Kelder)")


# =========================================================
# 5. OCR FUNCTIE
# =========================================================
def lees_nummer_van_foto(image_bytes):
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)

    response = client.text_detection(image=image)

    if response.error.message:
        raise Exception(response.error.message)

    if not response.text_annotations:
        return None

    volledige_tekst = response.text_annotations[0].description

    cijfers = re.findall(r"\d+", volledige_tekst)
    if not cijfers:
        return None

    return max(cijfers, key=len)


# =========================================================
# 6. ZOEKLOGICA
# =========================================================
def zoek_fiets():
    raw = st.session_state.input_field
    if not raw:
        return

    clean = raw.upper().replace(" ", "").replace(".", "").replace("€", "")
    cijfers = re.findall(r"\d+", clean)
    if cijfers:
        clean = max(cijfers, key=len)

    try:
        resp = supabase.table("stock").select("*").eq("fietsnummer", clean).execute()
        if resp.data:
            st.session_state.scan_result = {
                "status": "found",
                "nummer": clean,
                "data": resp.data[0]
            }
        else:
            st.session_state.scan_result = {
                "status": "unknown",
                "nummer": clean
            }
    except Exception as e:
        st.error(f"Fout: {e}")


def annuleer():
    st.session_state.scan_result = None
    st.session_state.input_field = ""


def verwerk_bekend():
    res = st.session_state.scan_result
    if not res:
        return

    supabase.table("stock").update({
        "gescand": True,
        "gescand_op": datetime.utcnow().isoformat(),
        "gescand_door": scanner_naam,
        "filiaal": filiaal,
        "locatie": locatie
    }).eq("fietsnummer", res["nummer"]).execute()

    st.session_state.success_msg = f"✅ {res['nummer']} opgeslagen"
    annuleer()


def verwerk_onbekend():
    res = st.session_state.scan_result
    if not res:
        return

    st.session_state.unknown_items.insert(0, {
        "fietsnummer": res["nummer"],
        "gescand": True,
        "gescand_op": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "gescand_door": scanner_naam,
        "filiaal": filiaal,
        "locatie": locatie,
        "status": "NIET IN LIJST"
    })

    st.session_state.success_msg = f"⚠️ {res['nummer']} toegevoegd"
    annuleer()


# =========================================================
# 7. TABS
# =========================================================
tab_scan, tab_excel = st.tabs(["📷 SCANNER", "📊 EXCEL"])


# =========================================================
# TAB 1 – SCANNER
# =========================================================
with tab_scan:

    if st.session_state.success_msg:
        st.success(st.session_state.success_msg)
        st.session_state.success_msg = None

    st.subheader("📷 Scan via foto")

    foto = st.camera_input("Neem foto van label")

    if foto:
        try:
            nummer = lees_nummer_van_foto(foto.getvalue())
            if nummer:
                st.session_state.input_field = nummer
                zoek_fiets()
            else:
                st.warning("Geen nummer gevonden op de foto")
        except Exception as e:
            st.error(f"OCR fout: {e}")

    st.divider()

    st.info("Of typ / scan manueel en druk op ENTER")

    st.text_input(
        "Nummer",
        key="input_field",
        on_change=zoek_fiets
    )

    if st.session_state.scan_result:
        res = st.session_state.scan_result
        st.divider()

        if res["status"] == "found":
            fiets = res["data"]
            titel = f"{fiets.get('merk','')} {fiets.get('model','')} {fiets.get('kleur','')} {fiets.get('maat','')}".strip()

            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"🚲 {titel or 'Onbekend'}")
                st.caption(f"Nummer: {res['nummer']}")
                if fiets.get("gescand"):
                    st.warning(f"Al geteld door {fiets.get('gescand_door')}")

            with col2:
                st.button("✅ OPSLAAN", use_container_width=True, on_click=verwerk_bekend)
                st.button("❌ ANNULEER", use_container_width=True, on_click=annuleer)

        else:
            st.warning(f"⚠️ Nummer {res['nummer']} niet in database")
            col1, col2 = st.columns(2)
            with col1:
                st.button("✅ TOCH TOEVOEGEN", use_container_width=True, on_click=verwerk_onbekend)
            with col2:
                st.button("❌ NEGEREN", use_container_width=True, on_click=annuleer)


# =========================================================
# TAB 2 – EXCEL
# =========================================================
with tab_excel:
    st.header("Excel beheer")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📥 Download resultaten"):
            resp = supabase.table("stock").select("*").execute()
            df_db = pd.DataFrame(resp.data)
            df_unk = pd.DataFrame(st.session_state.unknown_items)

            df_final = pd.concat([df_db, df_unk], ignore_index=True) if not df_unk.empty else df_db

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df_final.to_excel(writer, index=False)

            st.download_button("Download Excel", buffer, "totaal.xlsx")

    with col2:
        upload = st.file_uploader("Nieuwe lijst uploaden", type=["xlsx"])
        if upload and st.button("🚀 Importeer"):
            df = pd.read_excel(upload)
            df.columns = [c.lower() for c in df.columns]

            if "fietsnummer" in df.columns:
                bar = st.progress(0)
                for i, row in df.iterrows():
                    data = row.to_dict()
                    data["fietsnummer"] = str(data["fietsnummer"])
                    data["gescand"] = False
                    supabase.table("stock").upsert(data, on_conflict="fietsnummer").execute()
                    if i % 10 == 0:
                        bar.progress(i / len(df))
                bar.progress(1.0)
                st.success("Import klaar")
