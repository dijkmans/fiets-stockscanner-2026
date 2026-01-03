import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import io
import time

# ============================
# 1. INITIALISATIE
# ============================
st.set_page_config(page_title="Stocktelling Check", layout="wide", initial_sidebar_state="collapsed")
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
# 3. FUNCTIES
# ============================
def zoek_fiets():
    """Zoekt de fiets op in de database op basis van de input"""
    raw_input = st.session_state.input_field
    if not raw_input:
        return

    # Schoonmaken
    clean_nr = raw_input.upper().replace(" ", "").replace(".", "").replace("€", "").strip()
    import re
    cijfers = re.findall(r'\d+', clean_nr)
    if cijfers:
        clean_nr = max(cijfers, key=len)

    # Zoek in database
    try:
        response = supabase.table("stock").select("*").eq("fietsnummer", clean_nr).execute()
        
        if response.data:
            # Gevonden!
            st.session_state.scan_result = {
                "status": "found",
                "data": response.data[0],
                "nummer": clean_nr
            }
        else:
            # Niet gevonden
            st.session_state.scan_result = {
                "status": "unknown",
                "nummer": clean_nr
            }
    except Exception as e:
        st.error(f"Zoekfout: {e}")

def reset_scan():
    """Maakt het veld leeg voor de volgende"""
    st.session_state.scan_result = None
    st.session_state.input_field = ""

# ============================
# 4. TABBLADEN
# ============================
tab_scan, tab_excel = st.tabs(["🔫 CONTROLE & SCAN", "📊 EXCEL BEHEER"])

# ---------------------------------------------------------
# TAB 1: DE SLIMME SCANNER
# ---------------------------------------------------------
with tab_scan:
    st.info("👇 Scan/Typ nummer en druk op ENTER. Controleer daarna de info.")

    # 1. HET INVOERVELD
    st.text_input(
        "Nummer:", 
        key="input_field", 
        on_change=zoek_fiets,
        placeholder="Scan hier..."
    )

    # 2. HET RESULTAAT
    if st.session_state.scan_result:
        res = st.session_state.scan_result
        st.divider()
        
        if res['status'] == 'found':
            # --- SCENARIO: FIETS BEKEND ---
            fiets = res['data']
            
            # SLIMME TRUC: We bouwen de tekst op uit wat we vinden in jouw database
            merk = fiets.get('merk') or ""
            model = fiets.get('model') or ""
            kleur = fiets.get('kleur') or ""
            maat = fiets.get('maat') or ""
            
            # Maak er een mooie zin van. Bv: "Tenways AGO X (50 L)"
            display_tekst = f"{merk} {model} {kleur} {maat}".strip()
            if not display_tekst:
                display_tekst = "Geen details in database (alleen nummer)"
            
            col_info, col_btn = st.columns([3, 1])
            
            with col_info:
                st.subheader(f"🚲 {display_tekst}")
                st.caption(f"Nummer: {res['nummer']}")
                
                if fiets.get('gescand'):
                    al_door = fiets.get('gescand_door', '?')
                    st.warning(f"⚠️ Let op: Deze is al geteld door {al_door}!")
            
            with col_btn:
                if st.button("✅ JA, KLOPT", type="primary", use_container_width=True):
                    # Opslaan
                    supabase.table("stock").update({
                        "gescand": True,
                        "gescand_op": datetime.utcnow().isoformat(),
                        "gescand_door": scanner_naam,
                        "filiaal": filiaal,
                        "locatie": locatie
                    }).eq("fietsnummer", res['nummer']).execute()
                    
                    st.success(f"Opgeslagen!")
                    time.sleep(1)
                    reset_scan()
                    st.rerun()

                if st.button("❌ Annuleer", use_container_width=True):
                    reset_scan()
                    st.rerun()

        elif res['status'] == 'unknown':
            # --- SCENARIO: ONBEKEND ---
            st.warning(f"⚠️ Nummer **{res['nummer']}** staat NIET in de Excel lijst.")
            
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("✅ Toch Toevoegen", type="primary"):
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
                    st.success("Toegevoegd aan onbekende lijst.")
                    time.sleep(1)
                    reset_scan()
                    st.rerun()
            
            with col_no:
                if st.button("❌ Nee, Foutje"):
                    reset_scan()
                    st.rerun()

    # Lijstje onbekend
    if st.session_state.unknown_items:
        st.divider()
        st.write("⚠️ **Onbekende scans:**")
        st.dataframe(pd.DataFrame(st.session_state.unknown_items))

    # Voortgang
    try:
        done = supabase.table("stock").select("fietsnummer", count="exact", head=True).eq("gescand", True).execute()
        total = supabase.table("stock").select("fietsnummer", count="exact", head=True).execute()
        if total.count:
            st.progress(done.count / total.count)
            st.caption(f"{done.count} / {total.count} geteld")
    except: pass


# ---------------------------------------------------------
# TAB 2: EXCEL BEHEER
# ---------------------------------------------------------
with tab_excel:
    st.header("Excel Beheer")
    
    col_up, col_down = st.columns(2)
    
    with col_down:
        st.subheader("📥 Download Resultaten")
        if st.button("🔄 Download Alles"):
            try:
                resp = supabase.table("stock").select("*").execute()
                df_db = pd.DataFrame(resp.data)
                df_unk = pd.DataFrame(st.session_state.unknown_items)
                
                df_final = pd.concat([df_db, df_unk], ignore_index=True) if not df_unk.empty else df_db
                
                if not df_final.empty:
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df_final.to_excel(writer, index=False)
                    st.download_button("📥 Download Excel", buffer, "stocktelling_totaal.xlsx")
                else:
                    st.warning("Geen data.")
            except Exception as e:
                st.error(f"Fout: {e}")

    with col_up:
        st.subheader("📤 Nieuwe Lijst Uploaden")
        uploaded_file = st.file_uploader("Kies Excel bestand", type=["xlsx"])
        if uploaded_file:
            st.info("⚠️ Dit voegt nieuwe fietsen toe. Bestaande data blijft behouden.")
            if st.button("🚀 Importeer"):
                try:
                    df_new = pd.read_excel(uploaded_file)
                    df_new.columns = [c.lower() for c in df_new.columns]
                    
                    if 'fietsnummer' in df_new.columns:
                        bar = st.progress(0)
                        total = len(df_new)
                        for i, row in df_new.iterrows():
                            # We sturen gewoon alles mee wat in de excel staat
                            # Supabase pakt automatisch de kolommen die matchen
                            data = row.to_dict()
                            # Zorg dat fietsnummer een string is
                            data['fietsnummer'] = str(data['fietsnummer'])
                            data['gescand'] = False
                            
                            try:
                                supabase.table("stock").upsert(data, on_conflict="fietsnummer").execute()
                            except: pass
                            if i % 10 == 0: bar.progress(i / total)
                        bar.progress(1.0)
                        st.success("Klaar!")
                    else:
                        st.error("Excel moet kolom 'fietsnummer' bevatten.")
                except Exception as e:
                    st.error(f"Fout: {e}")
