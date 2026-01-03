from dotenv import load_dotenv
import os
import json
from supabase import create_client

# env laden
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL of SUPABASE_KEY ontbreekt")

# client maken
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# data ophalen
res = supabase.table("stock").select("*").execute()
data = res.data or []

# JSON dump schrijven
outfile = "supabase_stock_dump.json"
with open(outfile, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Klaar. {len(data)} rijen geëxporteerd naar {outfile}")
