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

@st.cache_data
def load_stock(file):
    if file.name.lower().endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    # Kolommen opschonen
    df.columns = df.columns.str.strip()

    # Verplichte kolommen
    required = ["FietsNr", "Merk", "Model", "Filiaal"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Kolom ontbreekt: {col}")

    # FietsNr altijd als string behandelen
    df["FietsNr"] = df["FietsNr"].astype(str).str.strip()

    return df

if uploaded_file is None:
    st.info("Upload eerst een stocklijst om te starten.")
    st.stop()

try:
    df_stock = load_stock(uploaded_file)
    st.success(f"Stocklijst geladen: {len(df_stock)} fietsen")
except Exception as e:
    st.error(f"Fout bij laden stocklijst: {e}")
    st.stop()

# -------------------------------------------------
# 2. Session state
# -------------------------------------------------
if "telling_log" not in st.session_state:
    st.session_state.telling_log = pd.DataFrame(
        columns=[
            "Tijdstip",
            "FietsNr",
            "Merk",
            "Model",
            "Kleur",
            "Status",
            "Filiaal in lijst",
            "Geteld filiaal",
            "Filiaal correct",
            "Detail"
        ]
    )

# -------------------------------------------------
# 3. Locatie instellingen
# -------------------------------------------------
st.subheader("📍 Telling")

geteld_filiaal = st.selectbox(
    "Geteld filiaal",
    ["GEEL", "MOL", "BOCHOLT", "STRUCTABO", "HERSELT"]
)

detail = st.text_input(
    "Detail (bijv. rij, box, rek)",
    placeholder="Rij 1"
)

# -------------------------------------------------
# 4. Camera en OCR
# -------------------------------------------------
st.subheader("📸 Scan FietsNr")

img_file = st.camera_input("Maak een foto van de code")

if img_file:
    img = Image.open(img_file)

    with st.spinner("Code lezen..."):
        text = pytesseract.image_to_string(img)
        match = re.search(r"\b\d{5}\b", text)

    if not match:
        st.error("Geen 5-cijferige FietsNr herkend.")
    else:
        fiets_nr = match.group(0)
        row = df_stock[df_stock["FietsNr"] == fiets_nr]

        if row.empty:
            st.error(f"FietsNr {fiets_nr} niet gevonden in stocklijst.")
        else:
            r = row.iloc[0]

            filiaal_lijst = str(r.get("Filiaal", "")).strip()
            filiaal_ok = filiaal_lijst.upper() == geteld_filiaal.upper()

            if filiaal_ok:
                st.success("✅ Filiaal klopt met stocklijst")
            else:
                st.warning(f"⚠️ Filiaal wijkt af (lijst: {filiaal_lijst})")

            st.markdown(
                f"""
**Gevonden fiets**
- FietsNr: **{fiets_nr}**
- Merk: **{r.get("Merk", "")}**
- Model: **{r.get("Model", "")}**
- Kleur: {r.get("Kleur", "")}
- Status: {r.get("Status", "")}
- Filiaal in lijst: **{filiaal_lijst}**
"""
            )

            if st.button("✅ Bevestig en sla op"):
                nieuw = {
                    "Tijdstip": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "FietsNr": fiets_nr,
                    "Merk": r.get("Merk", ""),
                    "Model": r.get("Model", ""),
                    "Kleur": r.get("Kleur", ""),
                    "Status": r.get("Status", ""),
                    "Filiaal in lijst": filiaal_lijst,
                    "Geteld filiaal": geteld_filiaal,
                    "Filiaal correct": "JA" if filiaal_ok else "NEE",
                    "Detail": detail
                }

                st.session_state.telling_log = pd.concat(
                    [st.session_state.telling_log, pd.DataFrame([nieuw])],
                    ignore_index=True
                )

                st.success(f"Fiets {fiets_nr} opgeslagen")

# -------------------------------------------------
# 5. Overzicht en download
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
        file_name=f"telling_{geteld_filiaal}.csv",
        mime="text/csv"
    )
