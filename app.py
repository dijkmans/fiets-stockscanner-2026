import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re
from datetime import datetime

# -------------------------------------------------
# Pagina instellingen
# -------------------------------------------------
st.set_page_config(
    page_title="Stocktelling 2026",
    layout="centered"
)

st.title("🚲 Stocktelling Tool")

# -------------------------------------------------
# 1. Stocklijst uploaden
# -------------------------------------------------
st.subheader("📄 Stocklijst uploaden")

uploaded_file = st.file_uploader(
    "Upload je stocklijst (Excel of CSV)",
    type=["xlsx", "csv"]
)

@st.cache_data(show_spinner=False)
def load_stock_from_upload(file, filename):
    if filename.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    # ID altijd als string behandelen
    df["ID"] = df["ID"].astype(str).str.strip()
    return df

if uploaded_file is None:
    st.warning("Upload eerst een stocklijst om te starten.")
    st.stop()

try:
    df_stock = load_stock_from_upload(uploaded_file, uploaded_file.name)
    st.success(f"Stocklijst geladen: {len(df_stock)} items")
except Exception as e:
    st.error(f"Fout bij laden stocklijst: {e}")
    st.stop()

# -------------------------------------------------
# 2. Session state initialisatie
# -------------------------------------------------
if "telling_log" not in st.session_state:
    st.session_state.telling_log = pd.DataFrame(
        columns=[
            "Tijdstip",
            "ID",
            "Merk",
            "Type",
            "Locatie",
            "Detail"
        ]
    )

# -------------------------------------------------
# 3. Configuratie
# -------------------------------------------------
st.subheader("📍 Locatie")

locatie = st.selectbox(
    "Locatie",
    ["GEEL", "MOL", "BOCHOLT", "STRUCTABO", "HERSELT"]
)

detail = st.text_input(
    "Detail (bijv. Rij of Box)",
    placeholder="Rij 1"
)

# -------------------------------------------------
# 4. Camera / Scanner
# -------------------------------------------------
st.subheader("📸 Scan fiets-ID")

img_file = st.camera_input("Maak een foto van de code")

if img_file:
    img = Image.open(img_file)

    with st.spinner("Code zoeken..."):
        text = pytesseract.image_to_string(img)
        match = re.search(r"\b\d{5}\b", text)

    if match:
        fiets_id = match.group(0)
        info = df_stock[df_stock["ID"] == fiets_id]

        if not info.empty:
            merk = info.iloc[0]["Merk"]
            ftype = info.iloc[0]["Type"]

            st.info(f"**Gevonden:** {merk} – {ftype} (ID: {fiets_id})")

            if st.button("✅ Bevestig & sla op"):
                nieuw_item = {
                    "Tijdstip": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ID": fiets_id,
                    "Merk": merk,
                    "Type": ftype,
                    "Locatie": locatie,
                    "Detail": detail,
                }

                st.session_state.telling_log = pd.concat(
                    [
                        st.session_state.telling_log,
                        pd.DataFrame([nieuw_item]),
                    ],
                    ignore_index=True,
                )

                st.success(f"Fiets {fiets_id} opgeslagen.")
        else:
            st.error(f"ID {fiets_id} niet gevonden in stocklijst.")
    else:
        st.error("Geen 5-cijferige code herkend. Probeer scherper te focussen.")

# -------------------------------------------------
# 5. Overzicht & download
# -------------------------------------------------
st.divider()
st.subheader("📊 Tellingsoverzicht")

st.dataframe(
    st.session_state.telling_log,
    use_container_width=True
)

if not st.session_state.telling_log.empty:
    csv = st.session_state.telling_log.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download telling",
        data=csv,
        file_name=f"telling_{locatie}.csv",
        mime="text/csv",
    )
