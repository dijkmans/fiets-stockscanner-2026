# =========================================================
# STOCKTELLING PRO – MET GOOGLE OCR
# =========================================================

import os
import io
import re
from datetime import datetime

import streamlit as st
import pandas as pd
from supabase import create_client, Client
from google.cloud import vision
from dotenv import load_dotenv


# =========================================================
# 0. ENV + GOOGLE OCR CONFIG
# =========================================================
load_dotenv()

GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not GOOGLE_CREDENTIALS_FILE:
    st.error("GOOGLE_APPLICATION_CREDENTIALS ontbreekt in .env")
    st.stop()

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("SUPABASE_URL of SUPABASE_KEY ontbreekt in .env")
    st.stop()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS_FILE


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
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("Databaseverbinding mislukt")
    st.write(e)
    st.stop()


# =========================================================
# 3. SESSION STATE
# =========================================================
st.session_state.setdefault("scan_result", None)
st.session_state.setdefault("unknown_items", [])
st.session_state.setdefault("success_msg", None)
st.session_state.setdefault("input_field", "")


# =========================================================
# 4. INSTELLINGEN
# =========================================================
with st.expander("⚙️ Instellingen", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        filiaal = st.selectbox("Filiaal", ["GEEL", "MOL", "HERSELT", "BOCHOLT"])
        scanner_naam = st.text_input("Jouw naam", value="")
    with col2:
        locatie = st.text_input("Locatie (bv. Kelder)")


# =========================================================
# 5. OCR FUNCTIE
# =========================================================
def lees_nummer_van_foto(image_bytes: bytes) -> str | None:
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)

    response = client.text_detection(image=image)

    if response.error.message:
        raise RuntimeError(response.error.message)

    if not response.text_annotations:
        return None

    tekst = response.text_annotations[0].description
    cijfers = re.findall(r"\d+", tekst)

    if not cijfers:
        return None

    return max(cijfers, key=len)


# =========================================================
# 6. ZOEK + VERWERKING
# =========================================================
def zoek_fiets():
    raw = st.session_state.input_field.strip()
    if not raw:
        return

    clean = re.sub(r"\D", "", raw)

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
        st.error("Zoekfout")
        st.write(e)


def reset_scan():
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
    reset_scan()


def verwerk_onbekend():
    res = st.session_state.scan_result
    if not res:
        return

    st.session_state.unknown_items.insert(0, {
        "fietsnummer": res["nummer"],
        "gescand": True,
        "gescand_op": datetime.utcnow().isoformat(),
        "gescand_door": scanner_naam,
        "filiaal": filiaal,
        "locatie": locatie,
        "status": "NIET IN LIJST"
    })

    st.session_state.success_msg = f"⚠️ {res['nummer']} toegevoegd"
    reset_scan()


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

    foto = st.camera_input("Neem foto van label")

    if foto:
        try:
            nummer = lees_nummer_van_foto(foto.getvalue())
            if nummer:
                st.session_state.input_field = nummer
                zoek_fiets()
            else:
                st.warning("Geen nummer gevonden")
        except Exception as e:
            st.error("OCR fout")
            st.write(e)

    st.divider()

    st.text_input(
        "Nummer (manueel)",
        key="input_field",
        on_change=zoek_fiets
    )

    if st.session_state.scan_result:
        res = st.session_state.scan_result
        st.divider()

        if res["status"] == "found":
            fiets = res["data"]
            titel = f"{fiets.get('merk','')} {fiets.get('model','')} {fiets.get('maat','')}".strip()

            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(titel or "Onbekende fiets")
                st.caption(f"Nummer: {res['nummer']}")
                if fiets.get("gescand"):
                    st.warning(f"Al gescand door {fiets.get('gescand_door')}")

            with col2:
                st.button("✅ OPSLAAN", use_container_width=True, on_click=verwerk_bekend)
                st.button("❌ ANNULEER", use_container_width=True, on_click=reset_scan)

        else:
            st.warning(f"{res['nummer']} niet in database")
            col1, col2 = st.columns(2)
            with col1:
                st.button("✅ TOEVOEGEN", use_container_width=True, on_click=verwerk_onbekend)
            with col2:
                st.button("❌ NEGEREN", use_container_width=True, on_click=reset_scan)


# =========================================================
# TAB 2 – EXCEL
# =========================================================
with tab_excel:
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📥 Download resultaten"):
            resp = supabase.table("stock").select("*").execute()
            df_db = pd.DataFrame(resp.data)
            df_unk = pd.DataFrame(st.session_state.unknown_items)
            df_final = pd.concat([df_db, df_unk], ignore_index=True)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df_final.to_excel(writer, index=False)

            st.download_button("Download Excel", buffer, "stocktelling.xlsx")

    with col2:
        upload = st.file_uploader("Nieuwe lijst uploaden", type=["xlsx"])
        if upload and st.button("🚀 Importeer"):
            df = pd.read_excel(upload)
            df.columns = [c.lower() for c in df.columns]

            if "fietsnummer" not in df.columns:
                st.error("Kolom 'fietsnummer' ontbreekt")
            else:
                bar = st.progress(0.0)
                for i, row in df.iterrows():
                    data = row.to_dict()
                    data["fietsnummer"] = str(data["fietsnummer"])
                    data["gescand"] = False
                    supabase.table("stock").upsert(
                        data,
                        on_conflict="fietsnummer"
                    ).execute()
                    bar.progress((i + 1) / len(df))
                st.success("Import klaar")
