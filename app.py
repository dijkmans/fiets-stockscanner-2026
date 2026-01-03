import streamlit as st
import pandas as pd
from PIL import Image
import easyocr
import numpy as np
import re
from datetime import datetime

# Instellingen voor mobiel gebruik
st.set_page_config(page_title="Stocktelling 2026", layout="centered")

# 1. Scanner & Data laden
@st.cache_resource
def load_reader():
    # Laadt het OCR model (neuraal netwerk)
    return easyocr.Reader(['en'])

reader = load_reader()

@st.cache_data
def load_stock():
    # Laadt jouw specifieke CSV bestand
    try:
        df = pd.read_csv("Tweewielers-03-01-2026.xlsx - data.csv")
        df['ID'] = df['ID'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Fout bij laden stocklijst: {e}")
        return pd.DataFrame()

df_stock = load_stock()

# 2. Sessiegeheugen voor de telling
if 'telling_log' not in st.session_state:
    st.session_state.telling_log = pd.DataFrame(columns=["Tijdstip", "ID", "Merk", "Type", "Locatie", "Detail"])

st.title("📋 Stocktelling Tool")

# 3. Configuratie per scan
col1, col2 = st.columns(2)
with col1:
    locatie = st.selectbox("Huidige Locatie", ["GEEL", "MOL", "BOCHOLT", "STRUCTABO", "HERSELT"])
with col2:
    detail = st.text_input("Detail (bijv. Box/Rij)", placeholder="Rij 1")

# 4. Scanner Interface
img_file = st.camera_input("Scan sticker")

if img_file:
    img = Image.open(img_file)
    img_np = np.array(img)
    
    with st.spinner('Code herkennen...'):
        results = reader.readtext(img_np)
        full_text = " ".join([res[1] for res in results])
        # Zoek naar exact 5 cijfers
        match = re.search(r'\b\d{5}\b', full_text)
    
    if match:
        fiets_id = match.group(0)
        
        # Dubbele scan check
        is_dubbel = fiets_id in st.session_state.telling_log['ID'].values
        if is_dubbel:
            st.warning(f"⚠️ Let op: Fiets {fiets_id} is al gescand!")
        
        # Info opzoeken
        info = df_stock[df_stock['ID'] == fiets_id]
        
        if not info.empty:
            merk = info.iloc[0]['Merk']
            ftype = info.iloc[0]['Type']
            st.success(f"✅ Gevonden: {merk} - {ftype} (ID: {fiets_id})")
            
            if st.button("Bevestig & Voeg toe aan telling"):
                nieuw_item = {
                    "Tijdstip": datetime.now().strftime("%H:%M:%S"),
                    "ID": fiets_id,
                    "Merk": merk,
                    "Type": ftype,
                    "Locatie": locatie,
                    "Detail": detail
                }
                st.session_state.telling_log = pd.concat([st.session_state.telling_log, pd.DataFrame([nieuw_item])], ignore_index=True)
                st.balloons()
                st.toast(f"Fiets {fiets_id} opgeslagen!")
        else:
            st.error(f"❌ ID {fiets_id} niet gevonden in de stocklijst!")
    else:
        st.error("Geen 5-cijferige code gevonden. Probeer de camera dichterbij te houden.")

# 5. Tabel en Download
st.divider()
st.subheader("Huidige Telling")
st.dataframe(st.session_state.telling_log, use_container_width=True)

if not st.session_state.telling_log.empty:
    csv = st.session_state.telling_log.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Telling als CSV",
        data=csv,
        file_name=f"telling_{locatie}_{datetime.now().strftime('%d-%m-%y')}.csv",
        mime='text/csv',
    )