from dotenv import load_dotenv
import os
from supabase import create_client
from datetime import datetime

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

# insert test record
insert = supabase.table("sessions").insert({
    "naam": "test via powershell",
    "gsm": "0499000000",
    "aangemaakt_door": "local test",
    "actief": True
}).execute()

print("INSERT:", insert)

# read back
select = supabase.table("sessions").select("*").execute()
print("SELECT:", select)
