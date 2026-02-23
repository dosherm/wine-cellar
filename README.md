# 🍷 Dan's Wine Cellar

A personal wine cellar tracker backed by **Firebase Firestore**, hosted on **GitHub Pages**.

**Live Site:** https://dosherm.github.io/wine-cellar

---

## Setup (One-time, ~5 minutes)

### 1. Push this repo to GitHub

```bash
cd wine-cellar
git init
git add .
git commit -m "Initial wine cellar setup"
git remote add origin https://github.com/dosherm/wine-cellar.git
git push -u origin main
```

### 2. Enable GitHub Pages

1. Go to your repo on GitHub → **Settings → Pages**
2. Under **Source**, select **Deploy from a branch**
3. Choose **main** branch, **/ (root)** folder → **Save**
4. Your site will be live at: `https://dosherm.github.io/wine-cellar`

### 3. Seed your Firestore database

1. Open `https://dosherm.github.io/wine-cellar/seed.html` in your browser
2. Click **"Seed Firestore Database"**
3. Watch all 26 wines load in — takes about 30 seconds
4. Once done, click the link to go to your cellar

### 4. Secure your database (important after testing)

In [Firebase Console](https://console.firebase.google.com) → Firestore Database → **Rules**, update to:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /wines/{document} {
      allow read: if true;            // public reads for the website
      allow write: if false;          // no public writes (Claude uses REST API)
    }
  }
}
```

---

## Using the Site

The site at `https://dosherm.github.io/wine-cellar` lets you:

- **Filter** by status: All / Drink Now / Peak / Hold
- **Sort** by: Drink Urgency, Value (high→low), Vintage, Name, Country
- **Search** by wine name, variety, region, or producer
- See estimated **value**, **drink window**, and color-coded **urgency** for every bottle

---

## Adding New Wines (Ask Claude)

When you get a new bottle, just tell Claude:
> *"I just picked up a 2022 Caymus Cabernet Sauvignon Napa Valley. Add it to my cellar."*

Claude will:
1. Search the web for the wine's value and drinking window
2. Run `functions/wine_manager.py` to push it to Firestore
3. Confirm it's been added — it'll appear on your site immediately

---

## File Structure

```
wine-cellar/
├── index.html              # Main wine grid (GitHub Pages site)
├── seed.html               # One-time database seeder (run once)
├── README.md               # This file
└── functions/
    └── wine_manager.py     # Python functions Claude uses to manage wines
```

---

## Wine Document Schema

Each wine in Firestore has these fields:

| Field | Type | Example |
|---|---|---|
| `name` | string | "Barbaresco DOCG" |
| `producer` | string | "Gemma (Piedmont)" |
| `vintage` | string | "2018" |
| `variety` | string | "Nebbiolo" |
| `region` | string | "Barbaresco, Piedmont" |
| `country` | string | "Italy" |
| `classification` | string | "DOCG" |
| `value_low` | number | 25 |
| `value_high` | number | 40 |
| `value_mid` | number | 32.5 |
| `drink_from` | string | "2026" |
| `drink_by` | string | "2035" |
| `status` | string | "Hold" / "Peak" / "Drink Now" |
| `notes` | string | "Hold — Nebbiolo needs time" |
| `quantity` | number | 1 |
| `added_date` | string | "2026-02-23" |
| `last_updated` | string | "2026-02-23" |
