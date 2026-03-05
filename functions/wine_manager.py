"""
wine_manager.py — Dan's Wine Cellar Firebase Manager
=====================================================
Used by Claude to add new wines, update existing ones,
and query the cellar via the Firestore REST API.

Usage (Claude runs this internally):
    python wine_manager.py add   '{"name":"...","vintage":"2020",...}'
    python wine_manager.py list
    python wine_manager.py update <doc_id> '{"status":"Drink Now",...}'
    python wine_manager.py delete <doc_id>

⚠ DEPRECATION WARNING ⚠
-----------------------
This script uses an API key + the flat `wines` collection.
Once Google Auth security rules are tightened, all writes (and reads)
to the flat `wines` collection will return 403 PERMISSION_DENIED.

To continue using this script after the auth migration:
  1. GCP Console → IAM & Admin → Service Accounts → Create service account
  2. Grant role: Cloud Datastore User
  3. Create JSON key → download
  4. Use `google-auth` library to obtain a Bearer token:
       from google.oauth2 import service_account
       creds = service_account.Credentials.from_service_account_file(
           'key.json', scopes=['https://www.googleapis.com/auth/datastore'])
       creds.refresh(google.auth.transport.requests.Request())
       token = creds.token
  5. Pass `Authorization: Bearer {token}` header instead of `?key=API_KEY`
  6. Update all BASE_URL paths from `wines` → `users/{uid}/wines`
"""

import sys, json, requests
from datetime import date

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ID = "dans-wine-cellar"
API_KEY    = "AIzaSyBhmmAgAuBZ4mqjEr5CTolfbrPqK36s-aY"
BASE_URL   = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/wines"

# ── Firestore type helpers ────────────────────────────────────────────────────
def to_firestore(data: dict) -> dict:
    """Convert a plain dict to Firestore REST API fields format."""
    fields = {}
    for k, v in data.items():
        if v is None:
            fields[k] = {"nullValue": None}
        elif isinstance(v, bool):
            fields[k] = {"booleanValue": v}
        elif isinstance(v, int):
            fields[k] = {"integerValue": str(v)}
        elif isinstance(v, float):
            fields[k] = {"doubleValue": v}
        elif isinstance(v, str):
            fields[k] = {"stringValue": v}
        else:
            fields[k] = {"stringValue": str(v)}
    return {"fields": fields}

def from_firestore(doc: dict) -> dict:
    """Convert a Firestore REST response document to a plain dict."""
    out = {"id": doc.get("name", "").split("/")[-1]}
    for k, v in doc.get("fields", {}).items():
        if "stringValue"  in v: out[k] = v["stringValue"]
        elif "integerValue" in v: out[k] = int(v["integerValue"])
        elif "doubleValue"  in v: out[k] = float(v["doubleValue"])
        elif "booleanValue" in v: out[k] = v["booleanValue"]
        elif "nullValue"    in v: out[k] = None
        else: out[k] = str(v)
    return out

# ── CRUD operations ───────────────────────────────────────────────────────────
def add_wine(wine: dict) -> dict | None:
    """Add a new wine document to Firestore. Returns the created doc."""
    wine.setdefault("added_date",    date.today().isoformat())
    wine.setdefault("last_updated",  date.today().isoformat())
    wine.setdefault("quantity",      1)
    wine.setdefault("status",        "Hold")

    resp = requests.post(
        f"{BASE_URL}?key={API_KEY}",
        json=to_firestore(wine),
        timeout=10
    )
    if resp.status_code == 200:
        doc = from_firestore(resp.json())
        print(f"✅ Added: {wine.get('name')} ({wine.get('vintage','NV')})  —  ID: {doc['id']}")
        return doc
    else:
        print(f"❌ Add failed ({resp.status_code}): {resp.text}")
        return None

def list_wines() -> list[dict]:
    """List all wines in the cellar."""
    resp = requests.get(f"{BASE_URL}?key={API_KEY}&pageSize=200", timeout=10)
    if resp.status_code != 200:
        print(f"❌ List failed ({resp.status_code}): {resp.text}")
        return []
    data   = resp.json()
    docs   = data.get("documents", [])
    wines  = [from_firestore(d) for d in docs]
    print(f"🍷 {len(wines)} bottles in cellar:\n")
    for w in sorted(wines, key=lambda x: ({"Drink Now":0,"Peak":1,"Hold":2}.get(x.get("status",""),9))):
        val = f"${w.get('value_mid','?')}" if w.get('value_mid') else ""
        print(f"  [{w.get('status','?'):10}]  {w.get('name','?'):45}  {w.get('vintage','NV'):5}  {val}")
    return wines

def update_wine(doc_id: str, updates: dict) -> dict | None:
    """Update specific fields on a wine document."""
    updates["last_updated"] = date.today().isoformat()
    mask = "&".join([f"updateMask.fieldPaths={k}" for k in updates.keys()])
    resp = requests.patch(
        f"{BASE_URL}/{doc_id}?key={API_KEY}&{mask}",
        json=to_firestore(updates),
        timeout=10
    )
    if resp.status_code == 200:
        doc = from_firestore(resp.json())
        print(f"✅ Updated document {doc_id}: {list(updates.keys())}")
        return doc
    else:
        print(f"❌ Update failed ({resp.status_code}): {resp.text}")
        return None

def delete_wine(doc_id: str) -> bool:
    """Delete a wine document by ID."""
    resp = requests.delete(f"{BASE_URL}/{doc_id}?key={API_KEY}", timeout=10)
    if resp.status_code == 200:
        print(f"✅ Deleted document {doc_id}")
        return True
    else:
        print(f"❌ Delete failed ({resp.status_code}): {resp.text}")
        return False

def find_wine(name: str) -> list[dict]:
    """Find wines by partial name match."""
    all_wines = list_wines()
    matches = [w for w in all_wines if name.lower() in w.get("name","").lower()]
    if matches:
        print(f"\nMatched {len(matches)} wine(s):")
        for w in matches:
            print(f"  ID: {w['id']}  |  {w.get('name')}  {w.get('vintage','NV')}")
    else:
        print(f"No wines found matching '{name}'")
    return matches

# ── Wine schema template ──────────────────────────────────────────────────────
WINE_SCHEMA = {
    "name":           "",          # Full wine name
    "producer":       "",          # Winery / maker
    "vintage":        "",          # e.g. "2021" or "NV"
    "variety":        "",          # Grape variety or blend
    "region":         "",          # Sub-region / AVA
    "country":        "",          # Country
    "classification": "",          # DOC, DOCG, Gran Reserva, etc.
    "value_low":      0,           # Low value estimate ($)
    "value_high":     0,           # High value estimate ($)
    "value_mid":      0.0,         # Mid-point value ($)
    "drink_from":     "",          # e.g. "2026" or "Now"
    "drink_by":       "",          # e.g. "2032"
    "status":         "Hold",      # "Drink Now" | "Peak" | "Hold"
    "notes":          "",          # Tasting / cellar notes
    "quantity":       1,           # Number of bottles
    "added_date":     "",          # Auto-filled
    "last_updated":   "",          # Auto-filled
}

# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python wine_manager.py [add|list|update|delete|find] [args]")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "list":
        list_wines()

    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: python wine_manager.py add '{\"name\":\"...\", ...}'")
            print("\nSchema fields:")
            for k, v in WINE_SCHEMA.items():
                print(f"  {k}: {type(v).__name__}")
            sys.exit(1)
        wine_data = json.loads(sys.argv[2])
        add_wine(wine_data)

    elif cmd == "update":
        if len(sys.argv) < 4:
            print("Usage: python wine_manager.py update <doc_id> '{\"status\":\"Drink Now\"}'")
            sys.exit(1)
        update_wine(sys.argv[2], json.loads(sys.argv[3]))

    elif cmd == "delete":
        if len(sys.argv) < 3:
            print("Usage: python wine_manager.py delete <doc_id>")
            sys.exit(1)
        delete_wine(sys.argv[2])

    elif cmd == "find":
        if len(sys.argv) < 3:
            print("Usage: python wine_manager.py find 'partial wine name'")
            sys.exit(1)
        find_wine(sys.argv[2])

    elif cmd == "schema":
        print(json.dumps(WINE_SCHEMA, indent=2))

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: add, list, update, delete, find, schema")
