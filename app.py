import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from google.cloud import vision
from google.oauth2 import service_account
import re

# ============================
# 1. AUTHENTICATIE & CONFIG
# ============================
st.set_page_config(page_title="Stocktelling Vision", layout="wide", initial_sidebar_state="collapsed")
st.title("🚲 Stocktelling (Google Vision)")

# --- A. SUPABASE SETUP ---
SUPABASE_URL = "https://ubgyxilkcmzvtpxresos.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InViZ3l4aWxrY216dnRweHJlc29zIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzQzOTM1NiwiZXhwIjoyMDgzMDE1MzU2fQ.EhllRUxKxjcXFt3bSbiV0gs2v9LNLvn6aOeVkkZFviY"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"❌ Database fout: {e}")
    st.stop()

# --- B. GOOGLE VISION SETUP (Gerepareerd) ---

# Hier plakken we de sleutel precies zoals hij hoort, met echte witregels.
private_key_fixed = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDPmhlgeh41Gyk1
ks+jDJVILhooRog5KQpf5Qhl4ymOZIKsFlN1Jws9NJQaGzy8l7TrQvetQ0TId59K
YB3JhQgVCgSrgU9B47GVDYFJgMIYGs29BK8Qg3Eoq6l8GfJFAdFHWy5R3sfDnBrc
kV9OyUYE3aFk5e7n7fvgszkGk2KheR8mpTSHnTFEkW2FEHVf4iULS++kx0mWdxV+
N9HILJfhB/9zpj297oHR8MR7cMESurO2OWdV2ZGWx87JpzpXWIjO9vv+dCqjN0dq
uCwq3Qdz0R6EeMe/Os3wtyMRKdX95Jr1NmpEl54KGU/9d89T2hb9OWhR5a67VvXf
y3pltWidAgMBAAECggEAVxgwtkt1OdVjxACMELz6MfZ5bdUtWEGyAwocrFYRfJYJ
RjX1nGwdaHeS/KLZp8tDkQGe0/cpN6sLzlGlnYIsolr6G5Ob0yo5ua0ZRON6Sk+Q
adC5u0VRp3zhFVnzTGUXTgbgV2ONzjBDCq8IW47QS8FJcQGP6Yhrh9jYvzv9AH2F
BMNo4Slwjz4DqoRmk7UGzDNCmYfVowu6Y/7btYzlFFI8BapNluAhMPAiKZzNf1sc
DXm4E/X4mpDjxqkSGx2Qftf4Z4fphhTPyg0dPSI29OC96QVsmo4WNzJqytn+lQUM
NaXMiMgrkWetW6FXLAiLnPzv+1f+gIjtct06V9ulNwKBgQDs/Q20wX/Pb1ynsfnN
3+tmj88lm94TkkcOXFN4khFtv80ykXTOpWPDBAdnagBJ42SK/L0HLzd3+yIh4V0m
KCkyfPRpL3sAaXl/02DenY5dLeV0NG8wE4iWt7WMfz/g1N6jJB+xTCuFSuc9iCd/
yulzKXZtEQO/fBBlwY0+7rUIqwKBgQDgQYt9xqlA/v42H6lBHsoDoyphO5AsZ2bX
j4axPhufzxXl167C/ZR/eHnU0/WcdbeRBAgNqKo0YZyv6hLngQRtN4LrAajAGXBC
A0sJp3nlIacOCjFhtGB46wop5QoXIsKvWQiDKDCwhPQLdBxaTeDr9EU2y1wkasbt
troYDfNj1wKBgB3cnReDslkvDRvMX0/DwWPBBzcT9t28dtumYpY0waF0o6SVk4Re
br2qCkzLnJGy535j7mWzW2fw6xId1aDzOo20FRAT/YnFwJuMxQ4ICGJRYDJOURxb
ucBUEbpMZn4sFIm2CZBLqsg28gBc4a1Gojfyp4uCs1gzh9VqmCOv7HvVAoGALBqX
7XeZp+++XTSi2+zLPCXl2tOVCjaX0kMm8UrOsgJPQzHE7BJlFyDBjSrWfhvkqz+I
ue728nBUGYDGkQMdtMEbHU7pOkaGfmUZZ9+pKHgS278DcTzBUGahTBYAgwZSFZxE
AU9xK/Yp7Oq7/MKePql+x0T9bSgW0X+DX+G2gWcCgYEAievu05kEEeQPSmJCvWHm
9GTyDgcwgWoijtr7IR6NEPhgJoRns1GEOmnDq4v5mHGWuZEmu0OdKQmY5zZCV3wu
ynAqYEW2H1nsNsPSDz7WxDp9Yj8zuVvyQw4R3K022mdl4ZjWNXXPQEO+i2HJK7sT
cGt2zSsfFG9MjGuRpsvjNe4=
-----END PRIVATE KEY-----"""

google_creds_dict = {
  "type": "service_account",
  "project_id": "ocr-scanner-483222",
  "private_key_id": "6f4edf2ec0ccc82bbc6e560cc07b75a7f7dfa8ca",
  "private_key": private_key_fixed,
  "client_email": "fiets-scanner@ocr-scanner-483222.iam.gserviceaccount.com",
  "client_id": "110966983343932365234",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/fiets-scanner%40ocr-scanner-483222.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# Verbinding maken
try:
    credentials = service_account.Credentials.from_service_account_info(google_creds_dict)
    vision_client = vision.ImageAnnotatorClient(credentials=credentials)
except Exception as e:
    st.error(f"Fout met Google sleutel: {e}")
    st.stop()

if 'unknown_items' not in st.session_state:
    st.session_state.unknown_items = []

# ============================
# 3. INTERFACE
# ============================
st.divider()
col1, col2 = st.columns(2)
with col1:
    filiaal = st.selectbox("Filiaal", ["GEEL", "MOL", "HERSELT", "BOCHOLT"])
    scanner_naam = st.text_input("Jouw naam", value="Piet") 
with col2:
    locatie = st.text_input("Locatie (bv. Kelder)")

# ============================
# 4. CAMERA & GOOGLE SCAN
# ============================
st.divider()
st.subheader("📸 Maak een foto")

img_file = st.camera_input("Richt op het etiket")

if img_file:
    with st.spinner("Google is aan het lezen..."):
        try:
            # 1. Foto naar Google sturen
            content = img_file.getvalue()
            image = vision.Image(content=content)
            response = vision_client.text_detection(image=image)
            texts = response.text_annotations
            
            found_nr = ""
            
            # 2. Zoeken naar 5 cijfers
            if texts:
                full_text = texts[0].description
                # Zoek specifiek naar 5 cijfers
                matches = re.findall(r"\b\d{5}\b", full_text)
                if matches:
                    found_nr = matches[0]
            
            # 3. Verwerken
            if found_nr:
                st.success(f"🔍 Google zag: **{found_nr}**")
                
                # Check Database
                check = supabase.table("stock").select("*").eq("fietsnummer", found_nr).execute()
                
                if check.data:
                    # Bestaat -> Update
                    supabase.table("stock").update({
                        "gescand": True,
                        "gescand_op": datetime.utcnow().isoformat(),
                        "gescand_door": scanner_naam,
                        "filiaal": filiaal,
                        "locatie": locatie
                    }).eq("fietsnummer", found_nr).execute()
                    st.balloons()
                    st.success(f"✅ {found_nr} Opgeslagen!")
                else:
                    # Bestaat niet -> Onbekend lijstje
                    log_entry = {
                        "Nummer": found_nr, 
                        "Tijd": datetime.now().strftime("%H:%M"), 
                        "Locatie": locatie,
                        "Status": "Niet in lijst"
                    }
                    st.session_state.unknown_items.insert(0, log_entry)
                    st.warning(f"⚠️ {found_nr} staat niet in de lijst (toegevoegd aan overzicht hieronder).")
            else:
                st.error("Google zag wel tekst, maar geen fietsnummer (5 cijfers). Probeer dichterbij.")
                if texts:
                    with st.expander("Bekijk wat Google wél zag"):
                        st.text(texts[0].description)
                        
        except Exception as e:
            st.error(f"Fout bij scannen: {e}")

# ============================
# 5. LIJSTJE ONBEKEND
# ============================
if st.session_state.unknown_items:
    st.divider()
    st.write("⚠️ **Onbekende fietsen (Niet in stocklijst):**")
    df = pd.DataFrame(st.session_state.unknown_items)
    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download lijst (CSV)", csv, "onbekend.csv", "text/csv")
