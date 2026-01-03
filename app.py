import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
from datetime import datetime
import os
import re
from io import BytesIO
from supabase import create_client, Client

# ============================
# 1. INITIALISATIE (MET GROTE VERSIE-CHECK)
# ============================
st.set_page_config(page_title="Stocktelling Tool 2026", layout="wide")

# --- DEZE BALK MOET JE ZIEN OM ZEKER TE ZIJN ---
st.error("🔴 VERSIE CHECK: ZATERDAG 17:15 - ALS JE DIT ZIET, IS DE UPDATE GELUKT! 🔴")

st.title("🚲 Stocktelling Tool")

# --- CONFIGURATIE (JOUW ECHTE GEGEVENS) ---
SUPABASE_URL = "https://ubgyxilkcmzvtpxresos.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InViZ3l4aWxrY216dnRweHJlc29zIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzQzOTM1NiwiZXhwIjoyMDgzMDE1MzU2fQ.EhllRUxKxjcXFt3bSbiV0gs2v9LNLvn6aOeVkkZFviY"

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Configuratie-fout: URL of KEY ontbreekt.")
    st.stop()

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("❌ Kan geen verbinding maken met de database client.")
    st.write(e)
    st.stop()

# --- STATUS CHECK ---
try:
    count_result = supabase.table("stock").select("fietsnummer", count="exact", head=True).execute()
    aantal_in_db = count_result.count
    
    if aantal_in_db is not None and aantal_in_db > 0:
        st.success(f"✅ Systeem is online. Huidige voorraad in database: **{aantal_in_db} fietsen**.")
    else:
        st.warning("⚠️ De database is nog leeg. Upload hieronder je eerste stocklijst.")
except Exception:
    st.warning("Kon database-status niet ophalen.")

# ============================
# 2. EXCEL UPLOAD
# ============================
st.header("📄 Stap 1: Voorraadlijst inladen")

uploaded_file = st.file_uploader("Upload de systeem-dump (Excel of CSV)", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        df.columns = [str(c).strip().lower() for c in df.columns]
        
        st.info(f"Bestand geladen met {len(df)} rijen. Beschikbare kolommen: {', '.join(df.columns)}")

        if st.button("📥 Start Import naar Supabase"):
            with st.spinner("Database controleren en data uploaden..."):
                try:
                    bestaande_data = supabase.table("stock").select("fietsnummer").execute().data
                    bestaande_nrs = {str(r["fietsnummer"]) for r in (bestaande_data or [])}
                except Exception as db_err:
                    st.error("❌ Kan tabel niet lezen.")
                    st.stop()

                nieuw = []
                for _, row in df.iterrows():
                    raw_nr = row.get("fietsnr") or row.get("fietsnummer") or row.get("fiets_nr")
                    if pd.isna(raw_nr): continue
                    
                    fietsnummer = str(raw_nr).split('.')[0].strip()

                    if fietsnummer and fietsnummer not in bestaande_nrs:
                        nieuw.append({
                            "fietsnummer": fietsnummer,
                            "merk": str(row.get("merk", "")).strip(),
                            "model": str(row.get("model", "")).strip(),
                            "maat": str(row.get("maat", "")).strip(),
                            "gescand": False
                        })

                if nieuw:
                    try:
                        for i in range(0, len(nieuw), 100):
                            batch = nieuw[i:i+100]
                            supabase.table("stock").insert(batch).execute()
                        st.success(f"✅ Succes! {len(nieuw)} fietsen toegevoegd.")
                        import time
                        time.sleep(1)
                        st.rerun() 
                    except Exception as ins_err:
                        st.error("❌ Fout bij schrijven.")
                else:
                    st.info("Geen nieuwe fietsen gevonden.")

    except Exception as e:
        st.error("Fout bij bestand.")

# ============================
# 3. SCANNER INTERFACE
# ============================
st.divider()
st.header("📸 Stap 2: Fietsen scannen")

col1, col2 = st.columns(2)
with col1:
    filiaal = st.selectbox("Filiaal", ["GEEL", "MOL", "HERSELT", "BOCHOLT"])
    scanner_naam = st.text_input("Naam van de teller")
with col2:
    locatie = st.text_input("Locatie")

foto = st.camera_input("Maak een foto")

def extract_fietsnummer(text):
    text = text.upper()
    matches = re.findall(r"[A-Z0-9\-]{4,}", text)
    return matches[0] if matches else ""

if foto:
    img = Image.open(foto)
    raw_text = pytesseract.image_to_string(img)
    herkend_nr = extract_fietsnummer(raw_text)

    st.subheader(f"🔍 Herkend: {herkend_nr}")

    if herkend_nr and scanner_naam and locatie:
        if st.button("✅ Bevestig scan"):
            try:
                res = supabase.table("stock").update({
                    "gescand": True,
                    "gescand_op": datetime.utcnow().isoformat(),
                    "gescand_door": scanner_naam,
                    "filiaal": filiaal,
                    "locatie": locatie
                }).eq("fietsnummer", herkend_nr).execute()

                if res.data:
                    st.success("Opgeslagen!")
                else:
                    st.error("Nummer niet in database.")
            except Exception as e:
                st.error("Fout bij opslaan.")

# ============================
# 4. OVERZICHT
# ============================
st.divider()
st.header("📊 Stap 3: Status")

if st.button("🔄 Ververs"):
    st.rerun()

try:
    res_all = supabase.table("stock").select("*").execute()
    if res_all.data:
        df_status = pd.DataFrame(res_all.data)
        st.metric("Totaal Gescand", df_status['gescand'].sum())
        st.dataframe(df_status, use_container_width=True)
except:
    pass