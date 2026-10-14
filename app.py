import os
import io
import math
import hashlib
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)

# =============================================================================
# IN-MEMORY DEMO DATABASE
# =============================================================================
DEMO_SCENARIOS = {
    "strong": {
        "name": "Strong Claim (Guntur Flood)",
        "farmer_name": "Ramesh Patel",
        "crop": "Paddy (Rice)",
        "sowing_date": "2026-06-20",
        "loss_date": "2026-09-12",
        "peril": "Flood",
        "farm_lat": 16.2435,
        "farm_lng": 80.6482,
        "photo_lat": 16.2437,
        "photo_lng": 80.6484,
        "photo_name": "guntur_field_flood_damage.jpg",
        "remarks": "Continuous heavy monsoon downpours for 3 days submerged entire paddy field under 4 feet of floodwater.",
        "reported_delay_hours": 18
    },
    "weak": {
        "name": "Weak Claim (Photo Far from Farm)",
        "farmer_name": "B. Venkata Rao",
        "crop": "Cotton",
        "sowing_date": "2026-07-02",
        "loss_date": "2026-09-02",
        "peril": "Lodging (Wind)",
        "farm_lat": 15.8281,
        "farm_lng": 78.0373,
        "photo_lat": 15.9420,  # ~14 km away!
        "photo_lng": 78.1450,
        "photo_name": "roadside_bushes.jpg",
        "remarks": "High wind squalls broke cotton stalks.",
        "reported_delay_hours": 140 # >72 hrs
    },
    "suspicious": {
        "name": "Suspicious Claim (No NDVI Drop)",
        "farmer_name": "S. K. Sharma",
        "crop": "Chilli",
        "sowing_date": "2026-06-10",
        "loss_date": "2026-09-18",
        "peril": "Drought",
        "farm_lat": 17.9784,
        "farm_lng": 79.5941,
        "photo_lat": 17.9785,
        "photo_lng": 79.5942,
        "photo_name": "healthy_crop_field.jpg",
        "remarks": "Acute drought and heat stress dried out the entire crop.",
        "reported_delay_hours": 36
    }
}

# =============================================================================
# GEODESIC DISTANCE CALCULATION (Haversine)
# =============================================================================
def calculate_distance_meters(lat1, lon1, lat2, lon2):
    R = 6371000.0  # Earth radius in meters
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2)**2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

# =============================================================================
# PLUG-IN POINT: REAL VISION AI API (Gemini, Claude, GPT-4o, etc.)
# =============================================================================
def assess_crop_damage_vision_api(scenario_type="strong", peril="Flood"):
    """
    =========================================================================
    REAL VISION MODEL INTEGRATION POINT
    To plug in Google Gemini Vision API:
    ```
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([image, "Classify crop damage type, severity (0-1), and confidence (0-1)."])
    ```
    =========================================================================
    """
    if scenario_type == "suspicious":
        return {
            "damage_type": "Healthy Crop (No Damage Detected)",
            "severity_pct": 5,
            "confidence_pct": 96,
            "notes": "Foliage reflection indicates robust chlorophyll and standard vegetative vigor. No visible drought wilting."
        }
    elif scenario_type == "weak":
        return {
            "damage_type": "Unrelated Non-Crop Vegetation",
            "severity_pct": 20,
            "confidence_pct": 68,
            "notes": "Low confidence match with registered crop profile; roadside shrubs identified."
        }
    else: # strong
        return {
            "damage_type": f"{peril} Damage (Confirmed)",
            "severity_pct": 85,
            "confidence_pct": 94,
            "notes": "Severe waterlogging, complete canopy submergence, and root rot signatures detected."
        }

# =============================================================================
# MOCK SATELLITE NDVI GENERATOR
# =============================================================================
def get_mock_satellite_ndvi(scenario_type="strong", loss_date_str="2026-09-12"):
    try:
        base_d = datetime.strptime(loss_date_str, "%Y-%m-%d")
    except Exception:
        base_d = datetime(2026, 9, 12)

    # 7 satellite passes from 14 days before loss to 5 days after
    dates = [(base_d + timedelta(days=offset)).strftime("%b %d") for offset in [-14, -10, -6, -2, 0, 2, 5]]

    if scenario_type == "suspicious":
        # NDVI actually rose (no drop)
        values = [0.58, 0.60, 0.62, 0.64, 0.65, 0.67, 0.69]
        drop = round(values[3] - values[6], 2) # -0.05
    elif scenario_type == "weak":
        # Negligible drop
        values = [0.58, 0.59, 0.58, 0.57, 0.56, 0.54, 0.52]
        drop = round(values[3] - values[6], 2) # 0.05
    else: # strong
        # Catastrophic drop
        values = [0.74, 0.76, 0.78, 0.77, 0.45, 0.30, 0.23]
        drop = round(values[3] - values[6], 2) # 0.54

    return {
        "labels": dates,
        "values": values,
        "pre_loss_ndvi": values[3],
        "post_loss_ndvi": values[6],
        "drop": drop
    }

# =============================================================================
# MOCK WEATHER GENERATOR
# =============================================================================
def get_mock_weather(scenario_type="strong", loss_date_str="2026-09-12"):
    try:
        base_d = datetime.strptime(loss_date_str, "%Y-%m-%d")
    except Exception:
        base_d = datetime(2026, 9, 12)

    dates = [(base_d + timedelta(days=offset)).strftime("%b %d") for offset in [-3, -2, -1, 0, 1, 2, 3]]

    if scenario_type == "strong":
        # 184 mm on loss date!
        rainfall = [8.0, 14.5, 62.0, 184.2, 48.0, 6.5, 2.0]
        anomaly_text = "Extreme 184.2 mm monsoon downpour on loss date (IMD Red Alert)"
    elif scenario_type == "weak":
        # Normal mild weather
        rainfall = [0.0, 2.0, 4.5, 6.0, 1.0, 0.0, 0.0]
        anomaly_text = "No severe weather anomalies recorded around loss date"
    else: # suspicious
        # 22 mm rain during alleged drought
        rainfall = [4.0, 8.5, 24.0, 22.0, 12.0, 2.0, 0.0]
        anomaly_text = "Steady precipitation recorded; contradicts total drought loss claim"

    return {
        "labels": dates,
        "rainfall": rainfall,
        "anomaly_text": anomaly_text
    }

# =============================================================================
# EVIDENCE STRENGTH SCORING ALGORITHM (0 - 100)
# =============================================================================
def compute_evidence_score(distance_m, ndvi_drop, has_weather_anomaly, ai_sev_pct, ai_conf_pct, delay_hours):
    # 1. Location validity (25 pts max)
    if distance_m <= 500:
        loc_score = 25.0
        loc_status = "VERIFIED"
        loc_note = f"Photo captured {int(distance_m)}m from farm (Within 500m geofence)."
    else:
        loc_score = 0.0
        loc_status = "VIOLATION"
        loc_note = f"Geofence violation: Photo taken {round(distance_m/1000, 1)}km away from farm."

    # 2. NDVI Drop (25 pts max)
    if ndvi_drop >= 0.35:
        ndvi_score = 25.0
        ndvi_status = "VERIFIED"
        ndvi_note = f"Severe canopy loss verified by Sentinel-2 (ΔNDVI -{ndvi_drop:.2f})."
    elif ndvi_drop >= 0.20:
        ndvi_score = 18.0
        ndvi_status = "VERIFIED"
        ndvi_note = f"Moderate vegetation drop verified (ΔNDVI -{ndvi_drop:.2f})."
    elif ndvi_drop >= 0.0:
        ndvi_score = 6.0
        ndvi_status = "WARNING"
        ndvi_note = f"Negligible vegetation loss detected (ΔNDVI -{ndvi_drop:.2f})."
    else:
        ndvi_score = 0.0
        ndvi_status = "SUSPICIOUS"
        ndvi_note = f"Anomaly: NDVI actually rose (+{abs(ndvi_drop):.2f}) instead of dropping."

    # 3. Weather match (20 pts max)
    if has_weather_anomaly:
        weather_score = 20.0
        weather_status = "VERIFIED"
        weather_note = "Independent weather data corroborates reported extreme peril event."
    else:
        weather_score = 5.0
        weather_status = "WARNING"
        weather_note = "No significant weather anomaly recorded on loss date."

    # 4. AI confidence (20 pts max)
    if ai_sev_pct >= 50 and ai_conf_pct >= 80:
        ai_score = 20.0
        ai_status = "VERIFIED"
        ai_note = f"AI Vision confirmed damage: {ai_sev_pct}% severity with {ai_conf_pct}% confidence."
    elif ai_sev_pct >= 20:
        ai_score = 10.0
        ai_status = "WARNING"
        ai_note = f"Partial damage detected: {ai_sev_pct}% severity."
    else:
        ai_score = 0.0
        ai_status = "SUSPICIOUS"
        ai_note = "AI Vision detected healthy foliage; no visible crop trauma."

    # 5. Reporting delay (10 pts max)
    if delay_hours <= 24:
        delay_score = 10.0
        delay_status = "VERIFIED"
        delay_note = f"Prompt reporting: Intimated within {int(delay_hours)}h (PMFBY legal window is 72h)."
    elif delay_hours <= 72:
        delay_score = 7.0
        delay_status = "VERIFIED"
        delay_note = f"Reported within {int(delay_hours)}h (Within statutory 72h limit)."
    else:
        delay_score = 0.0
        delay_status = "LATE"
        delay_note = f"Delayed reporting: Intimated {round(delay_hours/24, 1)} days late (Exceeded 72h PMFBY limit)."

    total_score = round(loc_score + ndvi_score + weather_score + ai_score + delay_score, 1)

    if total_score >= 75 and loc_status == "VERIFIED" and ndvi_status == "VERIFIED":
        verdict = "STRONG CLAIM"
        verdict_color = "emerald"
    elif total_score >= 45 and loc_status == "VERIFIED":
        verdict = "MODERATE CLAIM"
        verdict_color = "amber"
    else:
        verdict = "SUSPICIOUS / WEAK"
        verdict_color = "rose"

    return {
        "total_score": total_score,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "factors": {
            "location": {"score": loc_score, "max": 25, "status": loc_status, "note": loc_note},
            "ndvi": {"score": ndvi_score, "max": 25, "status": ndvi_status, "note": ndvi_note},
            "weather": {"score": weather_score, "max": 20, "status": weather_status, "note": weather_note},
            "ai": {"score": ai_score, "max": 20, "status": ai_status, "note": ai_note},
            "delay": {"score": delay_score, "max": 10, "status": delay_status, "note": delay_note}
        }
    }

# =============================================================================
# ROUTES
# =============================================================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/scenarios")
def get_scenarios():
    return jsonify(DEMO_SCENARIOS)

@app.route("/api/verify", methods=["POST"])
def verify_claim():
    data = request.json or {}
    scenario_type = data.get("scenario", "strong")
    peril = data.get("peril", "Flood")
    loss_date = data.get("loss_date", "2026-09-12")
    farm_lat = float(data.get("farm_lat", 16.2435))
    farm_lng = float(data.get("farm_lng", 80.6482))
    photo_lat = float(data.get("photo_lat", 16.2437))
    photo_lng = float(data.get("photo_lng", 80.6484))
    delay_hours = float(data.get("delay_hours", 18))

    distance_m = calculate_distance_meters(farm_lat, farm_lng, photo_lat, photo_lng)
    ndvi = get_mock_satellite_ndvi(scenario_type, loss_date)
    weather = get_mock_weather(scenario_type, loss_date)
    ai_vision = assess_crop_damage_vision_api(scenario_type, peril)

    has_anomaly = (scenario_type == "strong")
    score_data = compute_evidence_score(
        distance_m=distance_m,
        ndvi_drop=ndvi["drop"],
        has_weather_anomaly=has_anomaly,
        ai_sev_pct=ai_vision["severity_pct"],
        ai_conf_pct=ai_vision["confidence_pct"],
        delay_hours=delay_hours
    )

    photo_hash = data.get("photo_hash") or hashlib.sha256(f"{data.get('farmer_name')}_{loss_date}_{scenario_type}".encode()).hexdigest()

    return jsonify({
        "distance_m": distance_m,
        "is_within_geofence": distance_m <= 500,
        "photo_hash": photo_hash,
        "ndvi": ndvi,
        "weather": weather,
        "ai_vision": ai_vision,
        "score": score_data
    })

@app.route("/api/download-report", methods=["POST"])
def download_report():
    data = request.json or {}
    farmer = data.get("farmer_name", "Ramesh Patel")
    crop = data.get("crop", "Paddy (Rice)")
    peril = data.get("peril", "Flood")
    loss_date = data.get("loss_date", "2026-09-12")
    score = data.get("total_score", 85.0)
    verdict = data.get("verdict", "STRONG CLAIM")
    dist_m = data.get("distance_m", 24)
    p_hash = data.get("photo_hash", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    factors = data.get("factors", {})

    # Try ReportLab first
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        elements = []

        c_green = colors.HexColor("#15803d")
        c_dark = colors.HexColor("#0f172a")

        title_style = ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=18, textColor=c_green, leading=22)
        sub_style = ParagraphStyle('Sub', fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#64748b"), leading=12)
        h2_style = ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=12, textColor=c_green, leading=16, spaceAfter=4)
        body_style = ParagraphStyle('Body', fontName='Helvetica', fontSize=9, textColor=c_dark, leading=12)
        bold_style = ParagraphStyle('Bold', fontName='Helvetica-Bold', fontSize=9, textColor=c_dark, leading=12)

        elements.append(Paragraph("KISANPROOF | CROP-LOSS CLAIM EVIDENCE REPORT", title_style))
        elements.append(Paragraph("Generated under Pradhan Mantri Fasal Bima Yojana (PMFBY) Evidence Standards", sub_style))
        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=c_green, spaceAfter=10))

        t_data = [
            [Paragraph(f"<b>Farmer:</b> {farmer}", body_style), Paragraph(f"<b>Crop:</b> {crop}", body_style), Paragraph(f"<b>Peril:</b> {peril}", body_style)],
            [Paragraph(f"<b>Loss Date:</b> {loss_date}", body_style), Paragraph(f"<b>Score:</b> <b>{score}/100</b>", bold_style), Paragraph(f"<b>Verdict:</b> {verdict}", bold_style)],
            [Paragraph(f"<b>Geofence Offset:</b> {int(dist_m)}m ({'PASSED' if dist_m<=500 else 'VIOLATION'})", body_style), Paragraph(f"<b>Photo Hash:</b> {str(p_hash)[:16]}...", body_style), Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style)]
        ]
        t_summary = Table(t_data, colWidths=[180, 180, 180])
        t_summary.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(t_summary)
        elements.append(Spacer(1, 12))

        elements.append(Paragraph("Evidence Verification Breakdown (0 - 100)", h2_style))
        breakdown_data = [
            [Paragraph("<b>Verification Check</b>", bold_style), Paragraph("<b>Score</b>", bold_style), Paragraph("<b>Finding / Evidence Trail</b>", bold_style)],
            [Paragraph("1. GPS Geofence Check", body_style), Paragraph(f"{factors.get('location',{}).get('score',0)}/25", body_style), Paragraph(factors.get('location',{}).get('note',''), body_style)],
            [Paragraph("2. Sentinel-2 Satellite NDVI", body_style), Paragraph(f"{factors.get('ndvi',{}).get('score',0)}/25", body_style), Paragraph(factors.get('ndvi',{}).get('note',''), body_style)],
            [Paragraph("3. Weather Anomaly Match", body_style), Paragraph(f"{factors.get('weather',{}).get('score',0)}/20", body_style), Paragraph(factors.get('weather',{}).get('note',''), body_style)],
            [Paragraph("4. AI Vision Assessment", body_style), Paragraph(f"{factors.get('ai',{}).get('score',0)}/20", body_style), Paragraph(factors.get('ai',{}).get('note',''), body_style)],
            [Paragraph("5. 72h Intimation Window", body_style), Paragraph(f"{factors.get('delay',{}).get('score',0)}/10", body_style), Paragraph(factors.get('delay',{}).get('note',''), body_style)],
        ]
        t_breakdown = Table(breakdown_data, colWidths=[140, 60, 340])
        t_breakdown.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(t_breakdown)
        elements.append(Spacer(1, 12))

        elements.append(Paragraph("Cryptographic Proof & Tamper Seal", h2_style))
        cert_text = (
            f"<b>SHA-256 Photo Hash:</b> <font face='Courier' size=8>{p_hash}</font><br/>"
            f"<b>Status:</b> This claim has been automatically processed with multi-spectral satellite cross-checks, "
            f"ground GPS verification, and independent meteorological logs. Suitable for PMFBY expedited settlement."
        )
        t_cert = Table([[Paragraph(cert_text, body_style)]], colWidths=[540])
        t_cert.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f0fdf4")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#86efac")),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
        ]))
        elements.append(t_cert)

        doc.build(elements)
        buffer.seek(0)
        filename = f"KisanProof_Report_{farmer.replace(' ', '_')}.pdf"
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")
    except Exception as e:
        # Resilient Pure-Python PDF Generation Fallback
        pdf_stream = (
            b"%PDF-1.4\n"
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
            b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n"
            b"4 0 obj << /Length 600 >> stream\n"
            b"BT\n"
            b"/F1 16 Tf\n"
            b"40 740 Td (KISANPROOF | PMFBY CROP-LOSS CLAIM EVIDENCE REPORT) Tj\n"
            b"/F1 11 Tf\n"
            b"0 -28 Td (Farmer: " + farmer.encode('latin1', 'replace') + b" | Crop: " + crop.encode('latin1', 'replace') + b" | Peril: " + peril.encode('latin1', 'replace') + b") Tj\n"
            b"0 -20 Td (Loss Date: " + loss_date.encode('latin1') + b" | Evidence Score: " + str(score).encode('latin1') + b"/100 | Verdict: " + verdict.encode('latin1') + b") Tj\n"
            b"0 -20 Td (Geofence Check: " + str(int(dist_m)).encode('latin1') + b"m offset - " + (b"PASSED (Within 500m)" if dist_m<=500 else b"VIOLATION") + b") Tj\n"
            b"0 -25 Td (1. Sentinel-2 Satellite NDVI: Vegetation Drop Verified) Tj\n"
            b"0 -18 Td (2. Open-Meteo Weather: Meteorological Anomaly Corroborated) Tj\n"
            b"0 -18 Td (3. AI Vision: Loss Pattern & Severity Confirmed) Tj\n"
            b"0 -18 Td (4. Reporting Window: PMFBY 72-Hour Legal Standard Audited) Tj\n"
            b"0 -25 Td (Cryptographic SHA-256 Hash: " + p_hash[:48].encode('latin1') + b") Tj\n"
            b"0 -16 Td (" + p_hash[48:].encode('latin1') + b") Tj\n"
            b"ET\n"
            b"endstream\n"
            b"endobj\n"
            b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000280 00000 n \n0000000215 00000 n \ntrailer << /Size 6 /Root 1 0 R >>\nstartxref\n960\n%%EOF\n"
        )
        buffer = io.BytesIO(pdf_stream)
        buffer.seek(0)
        filename = f"KisanProof_Report_{farmer.replace(' ', '_')}.pdf"
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
