import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re
from datetime import datetime

# Instellingen
st.set_page_config(page_title="Stocktelling 2026", layout="centered")

# 1. Data laden
@st.cache_data
def load_stock():
    try:
        # Exacte naam van jouw bestand
        df = pd.read_csv("Tweewielers-03-01-2026.xlsx - data.csv")
        df['ID'] = df['ID'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Bestand niet gevonden: {e}")
        return pd.DataFrame()

df_stock = load_stock()

if 'telling_log' not in st.session_state:
    st.session_state.telling_log = pd.DataFrame(columns=["Tijdstip", "ID", "Merk", "Type", "Locatie", "Detail"])

st.title("🚲 Stocktelling Tool")

# 2. Configuratie
locatie = st.selectbox("Locatie", ["GEEL", "MOL", "BOCHOLT", "STRUCTABO", "HERSELT"])
detail = st.text_input("Detail (bijv. Rij of Box)", placeholder="Rij 1")

# 3. Scanner
img_file = st.camera_input("Maak een foto van de code")

if img_file:
    img = Image.open(img_file)
    
    with st.spinner('Code zoeken...'):
        # OCR via pytesseract (lichter voor Vercel)
        text = pytesseract.image_to_string(img)
        match = re.search(r'\b\d{5}\b', text)
    
    if match:
        fiets_id = match.group(0)
        info = df_stock[df_stock['ID'] == fiets_id]
        
        if not info.empty:
            merk = info.iloc[0]['Merk']
            ftype = info.iloc[0]['Type']
            st.info(f"**Gevonden:** {merk} - {ftype} (ID: {fiets_id})")
            
            if st.button("✅ Bevestig & Sla op"):
                nieuw_item = {
                    "Tijdstip": datetime.now().strftime("%H:%M:%S"),
                    "ID": fiets_id,
                    "Merk": merk,
                    "Type": ftype,
                    "Locatie": locatie,
                    "Detail": detail
                }
                st.session_state.telling_log = pd.concat([st.session_state.telling_log, pd.DataFrame([nieuw_item])], ignore_index=True)
                st.success(f"Fiets {fiets_id} opgeslagen.")
        else:
            st.error(f"ID {fiets_id} niet in stocklijst.")
    else:
        st.error("Geen 5-cijferige code herkend. Probeer scherper te focussen.")

# 4. Tabel en Download
st.divider()
st.dataframe(st.session_state.telling_log, use_container_width=True)

if not st.session_state.telling_log.empty:
    csv = st.session_state.telling_log.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Telling", data=csv, file_name=f"telling_{locatie}.csv", mime='text/csv')