from medicine_info import MEDICINE_DATABASE
import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import vision
from pyzbar.pyzbar import decode
import cv2
import numpy as np
import requests

# ---------------- ENV ----------------
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../credentials/google_vision.json"

app = Flask(__name__)
CORS(app)

vision_client = vision.ImageAnnotatorClient()

# ---------------- OCR ----------------
def extract_text(image_bytes):
    image = vision.Image(content=image_bytes)
    response = vision_client.text_detection(image=image)
    return [t.description for t in response.text_annotations]

# ---------------- MEDICINE NAME ----------------
def extract_medicine_name(texts):
    blacklist = [
        "TABLET","CAPSULE","BATCH","EXP","MFG",
        "PHARMA","MG","ML","KEEP","STORE"
    ]

    candidates = []
    for t in texts:
        t = t.upper().strip()
        if len(t) < 5:
            continue
        if any(b in t for b in blacklist):
            continue
        if t.isalpha():
            candidates.append(t)

    return max(candidates, key=len) if candidates else "Unknown"

# ---------------- FEATURES ----------------
def extract_features(texts):
    f = {
        "strength": False,
        "manufacturer": False,
        "batch": False,
        "expiry": False
    }

    for t in texts:
        t = t.upper()
        if re.search(r"\d+\s?(MG|ML)", t):
            f["strength"] = True
        if "PHARMA" in t or "LTD" in t:
            f["manufacturer"] = True
        if re.search(r"(BATCH|LOT)", t):
            f["batch"] = True
        if re.search(r"(EXP|EXPIRY)", t):
            f["expiry"] = True

    return f

def scan_barcode(image_bytes):
    img = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8),
        cv2.IMREAD_COLOR
    )
    codes = decode(img)
    if codes:
        return codes[0].data.decode("utf-8")
    return None

def fetch_from_openfda(medicine_name):
    try:
        url = f'https://api.fda.gov/drug/label.json?search=openfda.brand_name:"{medicine_name}"&limit=1'

        response = requests.get(url)
        data = response.json()

        if "results" not in data:
            return {}

        drug = data["results"][0]

        return {
            "name": drug.get("openfda", {}).get("brand_name", [medicine_name])[0],
            "generic_name": drug.get("openfda", {}).get("generic_name", ["Not available"])[0],
            "type": drug.get("openfda", {}).get("product_type", ["Not available"])[0],  # ✅ FIXED
            "manufacturer": drug.get("openfda", {}).get("manufacturer_name", ["Not available"])[0],
            "used_for": drug.get("indications_and_usage", ["Not available"]),
            "how_to_use": drug.get("dosage_and_administration", ["Not available"])[0],
            "side_effects": drug.get("adverse_reactions", ["Not available"]),
            "when_not_to_use": drug.get("contraindications", ["Not available"]),
            "storage": drug.get("storage_and_handling", ["Not available"])[0],
            "prescription_required": "Check label"
        }

    except Exception as e:
        print("OpenFDA error:", e)
        return {}

def get_medicine_image(medicine_name):
    try:
        # Simple Google image placeholder approach
        # You can replace with real medicine image API later
        return f"https://source.unsplash.com/600x400/?medicine,{medicine_name}"
    except:
        return None

# ---------------- DECISION ----------------
def decide_status(features, known):
    score = sum(features.values()) + (2 if known else 0)

    if score >= 5:
        return "genuine", "92%"
    elif score >= 3:
        return "suspicious", "70%"
    else:
        return "counterfeit", "40%"

# ---------------- SINGLE IMAGE SCAN ----------------
@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "Image missing"}), 400

    image_bytes = request.files["image"].read()
    texts = extract_text(image_bytes)

    medicine = extract_medicine_name(texts)
    features = extract_features(texts)

    known = medicine.upper() in MEDICINE_DATABASE
    status, confidence = decide_status(features, known)

    # 🔥 Try OpenFDA first
    med_data = fetch_from_openfda(medicine)

    # 🔁 If OpenFDA fails, fallback to local DB
    if not med_data:
        med_data = MEDICINE_DATABASE.get(medicine.upper(), {})
    

    image_url = get_medicine_image(medicine)

    return jsonify({
        "medicine_name": medicine,
        "medicine_info": med_data,
        "image_url": image_url,
        "status": status,
        "confidence": confidence
    })

# ---------------- VIDEO SCAN (ROTATION SUPPORT) ----------------


@app.route("/scan-video", methods=["POST"])
def scan_video():
    frames = request.files.getlist("frames")

    found = {
        "medicine": None,
        "expiry": None,
        "batch": None,
        "barcode": None
    }

    for frame in frames:
        image_bytes = frame.read()
        texts = extract_text(image_bytes)

        for t in texts:
            t = t.upper()

            if not found["expiry"] and re.search(r"(EXP|EXPIRY).*?\d{2}/\d{2}", t):
                found["expiry"] = t

            if not found["batch"] and re.search(r"(BATCH|LOT).*?\w+", t):
                found["batch"] = t

        if not found["medicine"]:
            found["medicine"] = extract_medicine_name(texts)

        if all(found.values()):
            break

    # 🔥 MERGE MEDICINE DATABASE DATA
    raw_name = (found["medicine"] or "").upper()

    # 🔥 NORMALIZATION FIX
    med_key = raw_name.replace("®", "").replace("™", "").strip()

    # 🔥 SMART MATCH (partial + exact)
    # 🔥 Try OpenFDA first
    med_info = fetch_from_openfda(found["medicine"])

    # 🔁 Fallback to local DB if needed
    if not med_info:
        for key, value in MEDICINE_DATABASE.items():
            if key in med_key or med_key in key:
                med_info = value
                break   

    # 🔥 ATTACH SCAN DATA INTO MEDICINE INFO
    med_info = {
        **med_info,
        "batch": found["batch"],
        "expiry": found["expiry"],
        "barcode": found["barcode"]
    }
    print("FINAL MED KEY:", med_key)
    print("FOUND MED INFO:", MEDICINE_DATABASE.get(med_key))
    
    image_url = get_medicine_image(found["medicine"])
    image_url = None
    if found["medicine"]:
            image_url = f"https://source.unsplash.com/600x400/?medicine,{found['medicine']}"
    
    return jsonify({
        "medicine": found["medicine"],
        "image_url": image_url, 
        "medicine_info": {**med_info,
        "batch": found["batch"],
        "expiry": found["expiry"],
        "barcode": found["barcode"]
    },
    
})

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)