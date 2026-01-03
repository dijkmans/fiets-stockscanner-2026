import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import io

# ============================
# 1. INITIALISATIE
# ============================
st.set_page_config(page_title="Stocktelling Pro", layout="wide", initial_sidebar_state="collapsed")
st.title("🚲 Stocktelling & Beheer")

# Connectie
SUPABASE_URL = "https://ubgyxilkcmzvtpxresos.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InViZ3l4aWxrY216dnRweHJlc29zIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzQzOTM1NiwiZXhwIjoyMDgzMDE1MzU2fQ.EhllRUxKxjcXFt3bSbiV0gs2v9LNLvn6aOeVkkZFviY"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"❌ Database fout: {e}")
    st.stop()

# Hier bewaren we de onbekende fietsen tijdelijk
if 'unknown_items' not in st.session_state:
    st.session_state.unknown_items = []

# ============================
# 2. INSTELLINGEN
# ============================
with st.expander("⚙️ Instellingen (Filiaal & Naam)", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        filiaal = st.selectbox("Filiaal", ["GEEL", "MOL", "HERSELT", "BOCHOLT"])
        scanner_naam = st.text_input("Jouw naam", value="Piet") 
    with col2:
        locatie = st.text_input("Locatie (bv. Kelder)")

# ============================
# 3. TABBLADEN
# ============================
tab_scan, tab_excel = st.tabs(["🔫 SCANNER", "📊 EXCEL BEHEER"])

# ---------------------------------------------------------
# TAB 1: SCANNEN
# ---------------------------------------------------------
with tab_scan:
    st.info("👇 Gebruik Google Lens -> Kopiëren -> Hier Plakken.")
    
    with st.form("scan_form", clear_on_submit=True):
        fietsnummer = st.text_input("Nummer:", key="input_field")
        submitted = st.form_submit_button("✅ Verwerken", type="primary")

        if submitted and fietsnummer:
            # Schoonmaken
            clean_nr = fietsnummer.upper().replace(" ", "").replace(".", "").replace("€", "").strip()
            import re
            cijfers = re.findall(r'\d+', clean_nr)
            if cijfers:
                clean_nr = max(cijfers, key=len)

            try:
                # 1. Check Database
                check = supabase.table("stock").select("*").eq("fietsnummer", clean_nr).execute()
                
                if check.data:
                    # BEKEND: Update
                    supabase.table("stock").update({
                        "gescand": True,
                        "gescand_op": datetime.utcnow().isoformat(),
                        "gescand_door": scanner_naam,
                        "filiaal": filiaal,
                        "locatie": locatie
                    }).eq("fietsnummer", clean_nr).execute()
                    st.success(f"🎉 **{clean_nr}** Opgeslagen!")
                else:
                    # ONBEKEND: Voeg toe aan tijdelijke lijst
                    log_entry = {
                        "fietsnummer": clean_nr,
                        "gescand": True,
                        "gescand_op": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "gescand_door": scanner_naam,
                        "filiaal": filiaal,
                        "locatie": locatie,
                        "status": "NIET IN LIJST" # Dit labelt ze duidelijk
                    }
                    st.session_state.unknown_items.insert(0, log_entry) 
                    st.warning(f"⚠️ **{clean_nr}** onbekend. Toegevoegd aan sessie.")
            
            except Exception as e:
                st.error(f"Fout: {e}")

    # Tabel onbekende items
    if st.session_state.unknown_items:
        st.divider()
        st.write("⚠️ **Onbekende scans (Deze sessie):**")
        st.dataframe(pd.DataFrame(st.session_state.unknown_items), use_container_width=True)

    # Voortgang
    try:
        done = supabase.table("stock").select("fietsnummer", count="exact", head=True).eq("gescand", True).execute()
        total = supabase.table("stock").select("fietsnummer", count="exact", head=True).execute()
        if total.count:
            st.divider()
            st.progress(done.count / total.count)
            st.caption(f"Totaal: {done.count} / {total.count}")
    except: pass


# ---------------------------------------------------------
# TAB 2: EXCEL BEHEER (NU MET MERGE FUNCTIE)
# ---------------------------------------------------------
with tab_excel:
    st.header("Excel Beheer")
    
    col_up, col_down = st.columns(2)
    
    # --- DOWNLOAD (GECOMBINEERD) ---
    with col_down:
        st.subheader("📥 Alles Downloaden")
        st.write("Dit combineert de database én je onbekende scans in één bestand.")
        
        if st.button("🔄 Download Complete Lijst"):
            with st.spinner("Lijsten samenvoegen..."):
                try:
                    # 1. Haal Database op
                    response = supabase.table("stock").select("*").execute()
                    df_db = pd.DataFrame(response.data)
                    
                    # 2. Haal Onbekende items op (uit geheugen)
                    df_unknown = pd.DataFrame(st.session_state.unknown_items)
                    
                    # 3. Samenvoegen (als er onbekende zijn)
                    if not df_unknown.empty:
                        # Zorg dat de kolommen matchen voor een mooie lijst
                        df_final = pd.concat([df_db, df_unknown], ignore_index=True)
                    else:
                        df_final = df_db
                        
                    if not df_final.empty:
                        # Sorteren: Gescand eerst, daarna Status
                        if 'status' not in df_final.columns:
                            df_final['status'] = 'OK'
                        
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df_final.to_excel(writer, index=False, sheet_name='Totaaloverzicht')
                        
                        st.download_button(
                            label="📥 Download Excel (Totaal)",
                            data=buffer,
                            file_name=f"stocktelling_compleet_{datetime.now().strftime('%H%M')}.xlsx",
                            mime="application/vnd.ms-excel"
                        )
                        st.success(f"Lijst gegenereerd: {len(df_final)} regels.")
                    else:
                        st.warning("Nog geen data.")
                except Exception as e:
                    st.error(f"Fout: {e}")

    # --- UPLOAD ---
    with col_up:
        st.subheader("📤 Startlijst Uploaden")
        uploaded_file = st.file_uploader("Kies Excel bestand", type=["xlsx"])
        
        if uploaded_file:
            try:
                df_new = pd.read_excel(uploaded_file)
                st.write("Voorbeeld:", df_new.head())
                df_new.columns = [c.lower() for c in df_new.columns]
                
                if 'fietsnummer' in df_new.columns:
                    if st.button("🚀 Importeer in Database", type="primary"):
                        progress_bar = st.progress(0)
                        count = 0
                        total_rows = len(df_new)
                        
                        for index, row in df_new.iterrows():
                            data = {"fietsnummer": str(row['fietsnummer']), "gescand": False}
                            try:
                                supabase.table("stock").upsert(data, on_conflict="fietsnummer").execute()
                                count += 1
                            except: pass
                            if index % 10 == 0: progress_bar.progress(index / total_rows)
                        
                        progress_bar.progress(1.0)
                        st.success(f"Klaar! {count} fietsen toegevoegd.")
                else:
                    st.error("Excel moet kolom 'fietsnummer' bevatten.")
            except Exception as e:
                st.error(f"Fout: {e}")
