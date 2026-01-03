import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# ============================
# 1. INITIALISATIE (GEEN GOOGLE MEER)
# ============================
st.set_page_config(page_title="Stocktelling Definitief", layout="wide", initial_sidebar_state="collapsed")
st.title("🚲 Stocktelling")

# Supabase instellingen
SUPABASE_URL = "https://ubgyxilkcmzvtpxresos.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InViZ3l4aWxrY216dnRweHJlc29zIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzQzOTM1NiwiZXhwIjoyMDgzMDE1MzU2fQ.EhllRUxKxjcXFt3bSbiV0gs2v9LNLvn6aOeVkkZFviY"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"❌ Database fout: {e}")
    st.stop()

# Sessie status voor onbekende items
if 'unknown_items' not in st.session_state:
    st.session_state.unknown_items = []

# ============================
# 2. INSTELLINGEN
# ============================
st.divider()
col1, col2 = st.columns(2)
with col1:
    filiaal = st.selectbox("Filiaal", ["GEEL", "MOL", "HERSELT", "BOCHOLT"])
    scanner_naam = st.text_input("Jouw naam", value="Piet") 
with col2:
    locatie = st.text_input("Locatie (bv. Kelder)")

# ============================
# 3. SCAN & VERWERK (HET ECHTE WERK)
# ============================
st.divider()
st.info("👇 Klik hieronder. Gebruik Google Lens (app) om te scannen en PLAK het nummer hier.")

with st.form("scan_form", clear_on_submit=True):
    # Simpel tekstvak. Kan niet crashen.
    fietsnummer = st.text_input("Nummer:", key="input_field")
    submitted = st.form_submit_button("✅ Verwerken")

    if submitted and fietsnummer:
        # Maak schoon (hoofdletters, spaties weg, puntjes weg)
        clean_nr = fietsnummer.upper().replace(" ", "").replace(".", "").replace("€", "").strip()
        
        # Soms leest Google "42 228". Dit filtert alleen de cijfers eruit als het een rommeltje is.
        import re
        cijfers = re.findall(r'\d+', clean_nr)
        if cijfers:
            clean_nr = "".join(cijfers)

        try:
            # 1. Check Database
            check = supabase.table("stock").select("*").eq("fietsnummer", clean_nr).execute()
            
            if check.data:
                # 2. UPDATE (Bestaat)
                supabase.table("stock").update({
                    "gescand": True,
                    "gescand_op": datetime.utcnow().isoformat(),
                    "gescand_door": scanner_naam,
                    "filiaal": filiaal,
                    "locatie": locatie
                }).eq("fietsnummer", clean_nr).execute()
                st.success(f"🎉 **{clean_nr}** Opgeslagen!")
                
            else:
                # 3. ONBEKEND (Bestaat niet)
                log_entry = {
                    "Nummer": clean_nr,
                    "Tijd": datetime.now().strftime("%H:%M"),
                    "Locatie": locatie,
                    "Status": "Niet in lijst"
                }
                st.session_state.unknown_items.insert(0, log_entry) 
                st.warning(f"⚠️ **{clean_nr}** staat niet in de lijst (toegevoegd aan tabel hieronder).")
        
        except Exception as e:
            st.error(f"Fout: {e}")

# ============================
# 4. LIJST ONBEKENDE ITEMS
# ============================
if st.session_state.unknown_items:
    st.divider()
    st.write("⚠️ **Onbekende fietsen:**")
    df = pd.DataFrame(st.session_state.unknown_items)
    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV", csv, "onbekend.csv", "text/csv")

# ============================
# 5. PROGRESS BAR
# ============================
try:
    done = supabase.table("stock").select("fietsnummer", count="exact", head=True).eq("gescand", True).execute()
    total = supabase.table("stock").select("fietsnummer", count="exact", head=True).execute()
    if total.count:
        st.divider()
        st.progress(done.count / total.count)
        st.caption(f"Totaal: {done.count} / {total.count}")
except: pass
