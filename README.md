# KisanProof: Crop-Loss Claim Evidence Generator

A fast, mobile-first PMFBY crop-loss claim evidence generator combining browser camera telemetry (GPS + SHA-256 tamper hash), mock Sentinel-2 NDVI satellite drop analysis, Open-Meteo weather anomaly checks, and AI vision damage assessment into an Evidence Strength Score (0-100) with certified PDF generation.

## 🚀 Quick Start (Under 1 Minute)
```bash
# 1. Install dependencies
pip install flask reportlab

# 2. Run the application
python app.py

# 3. Open in your browser
http://localhost:5000
```

## 🎯 3-Minute Demo Script
1. Open `http://localhost:5000`.
2. Notice the **72-Hour PMFBY Statutory Countdown** banner warning farmers of the legal deadline.
3. In the top bar, select **🟢 Strong Claim (Flood ~85)**:
   - Notice the Leaflet farm pin at Guntur, AP.
   - Ground photo is within 24m of the farm (Geofence verified).
   - Chart.js shows Sentinel-2 NDVI drop from 0.77 to 0.23 (-0.54).
   - Weather chart highlights 184.2 mm extreme rainfall anomaly on loss date.
   - AI confirms flood damage with 94% confidence.
   - Evidence Score reaches **85/100 (Strong Claim)**.
4. Switch to **🟡 Weak Claim (Far ~35)**:
   - Photo was captured 14 km away from the farm (Geofence Violation flag in red).
   - Delayed intimation past 72h (140 hrs late). Score plunges to **~35/100**.
5. Switch to **🔴 Suspicious Claim (No Drop ~40)**:
   - Farmer claimed severe drought, but Sentinel-2 NDVI actually rose (+0.05) and AI detected healthy foliage. Flagged for surveyor scrutiny.
6. Click **"Download Official PMFBY Claim Report (PDF)"** at the bottom to generate and download the tamper-proof evidence dossier with cryptographic hashes.
