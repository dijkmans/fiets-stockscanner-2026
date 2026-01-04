import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import io
import time

# ============================
# 1. INITIALISATIE
# ============================
st.set_page_config(page_title="Stocktelling Pro", layout="wide", initial_sidebar_state="collapsed")
st.title("🚲 Stocktelling + Controle")

# Connectie
SUPABASE_URL = "https://ubgyxilkcmzvtpxresos.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InViZ3l4aWxrY216dnRweHJlc29zIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzQzOTM1NiwiZXhwIjoyMDgzMDE1MzU2fQ.EhllRUxKxjcXFt3bSbiV0gs2v9LNLvn6aOeVkkZFviY"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"❌ Database fout: {e}")
    st.stop()

# Sessie status initialiseren
if 'unknown_items' not in st.session_state:
    st.session_state.unknown_items = []
if 'scan_result' not in st.session_state:
    st.session_state.scan_result = None
if 'success_msg' not in st.session_state:
    st.session_state.success_msg = None

# ============================
# 2. INSTELLINGEN
# ============================
with st.expander("⚙️ Instellingen", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        filiaal = st.selectbox("Filiaal", ["GEEL", "MOL", "HERSELT", "BOCHOLT"])
        scanner_naam = st.text_input("Jouw naam", value="Piet") 
    with col2:
        locatie = st.text_input("Locatie (bv. Kelder)")

# ============================
# 3. FUNCTIES (CALLBACKS - DIT VOORKOMT DE CRASH)
# ============================
def zoek_fiets():
    """Zoekt direct zodra je op Enter drukt"""
    raw_input = st.session_state.input_field
    if not raw_input: return

    # Schoonmaken
    clean_nr = raw_input.upper().replace(" ", "").replace(".", "").replace("€", "").strip()
    import re
    cijfers = re.findall(r'\d+', clean_nr)
    if cijfers:
        clean_nr = max(cijfers, key=len)

    try:
        response = supabase.table("stock").select("*").eq("fietsnummer", clean_nr).execute()
        if response.data:
            st.session_state.scan_result = {"status": "found", "data": response.data[0], "nummer": clean_nr}
        else:
            st.session_state.scan_result = {"status": "unknown", "nummer": clean_nr}
    except Exception as e:
        st.error(f"Fout: {e}")

def verwerk_bekend():
    """Slaat een BEKENDE fiets op en reset het veld"""
    res = st.session_state.scan_result
    if res and res['status'] == 'found':
        supabase.table("stock").update({
            "gescand": True,
            "gescand_op": datetime.utcnow().isoformat(),
            "gescand_door": scanner_naam,
            "filiaal": filiaal,
            "locatie": locatie
        }).eq("fietsnummer", res['nummer']).execute()
        
        st.session_state.success_msg = f"✅ {res['nummer']} Opgeslagen!"
        # Resetten
        st.session_state.scan_result = None
        st.session_state.input_field = ""

def verwerk_onbekend():
    """Voegt een ONBEKENDE fiets toe en reset het veld"""
    res = st.session_state.scan_result
    if res and res['status'] == 'unknown':
        log_entry = {
            "fietsnummer": res['nummer'],
            "gescand": True,
            "gescand_op": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "gescand_door": scanner_naam,
            "filiaal": filiaal,
            "locatie": locatie,
            "status": "NIET IN LIJST"
        }
        st.session_state.unknown_items.insert(0, log_entry)
        
        st.session_state.success_msg = f"⚠️ {res['nummer']} toegevoegd aan lijst."
        # Resetten
        st.session_state.scan_result = None
        st.session_state.input_field = ""

def annuleer():
    """Gewoon resetten"""
    st.session_state.scan_result = None
    st.session_state.input_field = ""

# ============================
# 4. TABBLADEN
# ============================
tab_scan, tab_excel = st.tabs(["🔫 SCANNER", "📊 EXCEL"])

# ---------------------------------------------------------
# TAB 1: SCANNER
# ---------------------------------------------------------
with tab_scan:
    # Meldingen tonen van vorige actie
    if st.session_state.success_msg:
        st.success(st.session_state.success_msg)
        st.session_state.success_msg = None # Bericht weer weg na tonen

    st.info("👇 Scan nummer en druk op ENTER.")

    # Input veld
    st.text_input(
        "Nummer:", 
        key="input_field", 
        on_change=zoek_fiets, # Zoekt direct bij enter
        placeholder="..."
    )

    # Resultaat tonen
    if st.session_state.scan_result:
        res = st.session_state.scan_result
        st.divider()
        
        if res['status'] == 'found':
            # BEKEND
            fiets = res['data']
            merk = fiets.get('merk') or ""
            model = fiets.get('model') or ""
            kleur = fiets.get('kleur') or ""
            maat = fiets.get('maat') or ""
            
            display_tekst = f"{merk} {model} {kleur} {maat}".strip() or "Geen info"
            
            col1, col2 = st.columns([3,1])
            with col1:
                st.subheader(f"🚲 {display_tekst}")
                st.caption(f"Nummer: {res['nummer']}")
                if fiets.get('gescand'):
                    st.warning(f"⚠️ Al geteld door {fiets.get('gescand_door', '?')}")
            with col2:
                # DE OPLOSSING: on_click calls!
                st.button("✅ OPSLAAN", type="primary", use_container_width=True, on_click=verwerk_bekend)
                st.button("❌ ANNULEER", use_container_width=True, on_click=annuleer)

        elif res['status'] == 'unknown':
            # ONBEKEND
            st.warning(f"⚠️ Nummer **{res['nummer']}** staat NIET in de database.")
            col1, col2 = st.columns(2)
            with col1:
                st.button("✅ TOCH TOEVOEGEN", type="primary", use_container_width=True, on_click=verwerk_onbekend)
            with col2:
                st.button("❌ NEGEREN", use_container_width=True, on_click=annuleer)

    # Tabel onbekend
    if st.session_state.unknown_items:
        st.divider()
        st.write("⚠️ **Onbekende scans:**")
        st.dataframe(pd.DataFrame(st.session_state.unknown_items))

    # Progress
    try:
        done = supabase.table("stock").select("fietsnummer", count="exact", head=True).eq("gescand", True).execute()
        total = supabase.table("stock").select("fietsnummer", count="exact", head=True).execute()
        if total.count:
            st.progress(done.count / total.count)
            st.caption(f"{done.count} / {total.count}")
    except: pass

# ---------------------------------------------------------
# TAB 2: EXCEL
# ---------------------------------------------------------
with tab_excel:
    st.header("Excel Beheer")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Download Resultaten"):
            try:
                resp = supabase.table("stock").select("*").execute()
                df_db = pd.DataFrame(resp.data)
                df_unk = pd.DataFrame(st.session_state.unknown_items)
                df_final = pd.concat([df_db, df_unk], ignore_index=True) if not df_unk.empty else df_db
                
                if not df_final.empty:
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df_final.to_excel(writer, index=False)
                    st.download_button("📥 Download Excel", buffer, "totaal.xlsx")
            except Exception as e: st.error(f"Fout: {e}")
            
    with col2:
        uploaded_file = st.file_uploader("Nieuwe lijst uploaden", type=["xlsx"])
        if uploaded_file and st.button("🚀 Importeer"):
            try:
                df = pd.read_excel(uploaded_file)
                df.columns = [c.lower() for c in df.columns]
                if 'fietsnummer' in df.columns:
                    bar = st.progress(0)
                    for i, row in df.iterrows():
                        data = row.to_dict()
                        data['fietsnummer'] = str(data['fietsnummer'])
                        data['gescand'] = False
                        try: supabase.table("stock").upsert(data, on_conflict="fietsnummer").execute()
                        except: pass
                        if i%10==0: bar.progress(i/len(df))
                    bar.progress(1.0)
                    st.success("Klaar!")
            except Exception as e: st.error(f"Fout: {e}")
