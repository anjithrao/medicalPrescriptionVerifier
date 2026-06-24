from flask import Flask, request, jsonify, render_template, render_template_string, Response
import base64
import io
import json
import math
import os
import sys
import tempfile
from urllib.parse import quote_plus

import requests
import torch
from PIL import Image

app = Flask(__name__)


def load_env_file(path=".env"):
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


load_env_file()

print("Loading models...")

import easyocr
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

sys.path.insert(0, "crnn-pytorch")
from correct import correct, DICTIONARY

reader = easyocr.Reader(["en"], gpu=torch.cuda.is_available())
processor = TrOCRProcessor.from_pretrained("./trocr_best")
model = VisionEncoderDecoderModel.from_pretrained("./trocr_best")
model.eval()
if torch.cuda.is_available():
    model = model.cuda()

print("Models loaded.")

MEDICINE_PREFIXES = [
    "tab",
    "tab.",
    "cap",
    "cap.",
    "inj",
    "inj.",
    "syr",
    "syr.",
    "t.",
    "tb.",
    "c.",
    "oint",
    "drops",
]

KNOWN_MEDICINES = sorted(set(DICTIONARY))
GEMINI_MODEL = "gemini-2.5-flash"


def normalize_reference_key(name):
    return "".join(char for char in (name or "").lower() if char.isalnum())


def build_reference_info(uses="", side_effects=""):
    uses = (uses or "").strip()
    side_effects = (side_effects or "").strip()
    return {
        "found": bool(uses or side_effects),
        "uses": uses,
        "side_effects": side_effects,
    }


def load_reference_fallbacks_from_info(path="info_txt.txt"):
    if not os.path.exists(path):
        return {}

    fallback_map = {}
    current_name = ""
    current_uses = ""
    current_side_effects = ""

    def commit_current():
        if not current_name:
            return
        current_key = normalize_reference_key(current_name)
        known_key_map = {
            normalize_reference_key(known_name): known_name
            for known_name in KNOWN_MEDICINES
        }
        normalized_name = known_key_map.get(current_key, current_name.strip().lower())
        fallback_map[normalize_reference_key(normalized_name)] = {
            "uses": current_uses.strip(),
            "side_effects": current_side_effects.strip(),
        }

    with open(path, "r", encoding="utf-8") as info_file:
        for raw_line in info_file:
            line = raw_line.strip()
            if not line:
                continue
            if line.lower().startswith("uses:"):
                current_uses = line.split(":", 1)[1].strip()
                continue
            if line.lower().startswith("side effects:"):
                current_side_effects = line.split(":", 1)[1].strip()
                continue

            commit_current()
            current_name = line
            current_uses = ""
            current_side_effects = ""

    commit_current()
    return fallback_map


def build_reference_fallbacks():
    groups = [
        (
            ["allitose-sp"],
            "This medicine helps reduce pain and swelling in muscles and joints. It is often used for sprains or mild arthritis.",
            "Some people may feel stomach upset or mild nausea. Rarely, it can cause headaches or dizziness.",
        ),
        (
            ["alprazolam"],
            "This medicine helps calm anxiety and panic attacks. It can make people feel more relaxed and less worried.",
            "It can make you sleepy or tired. Long-term use may cause dependence.",
        ),
        (
            ["alprovit"],
            "This is a multivitamin that provides important vitamins for your body. It helps keep you healthy when your diet is not enough.",
            "Some people may feel mild stomach upset. Rarely, allergic reactions can occur.",
        ),
        (
            ["amlodipine", "stamlo"],
            "This medicine lowers high blood pressure. It also helps the heart pump blood more easily.",
            "It can cause swelling of the feet or ankles. Some people feel dizzy or tired.",
        ),
        (
            ["amoxicillin"],
            "This antibiotic treats bacterial infections like throat or ear infections. It helps your body fight harmful germs.",
            "It may cause diarrhea or stomach upset. Sometimes, it can cause a skin rash.",
        ),
        (
            ["amphogel"],
            "This medicine reduces stomach acid. It is used for heartburn, acidity, or ulcers.",
            "It may cause constipation. Rarely, long-term use can lower phosphate levels.",
        ),
        (
            ["arvast", "ator", "atorvastatin", "corestin", "novastat", "stator", "storvas"],
            "This medicine lowers high cholesterol in your blood. It helps reduce the risk of heart attacks or strokes.",
            "It may cause muscle pain or weakness. Some people may have changes in liver tests.",
        ),
        (
            ["ascoril", "solvin-cold"],
            "This medicine helps clear mucus from your lungs when you have cough or cold. It makes breathing easier.",
            "Some people may feel palpitations. It can also make you feel drowsy or sleepy.",
        ),
        (
            ["aspirin", "ecosprin"],
            "This medicine reduces pain, fever, and helps prevent blood clots in people at risk of heart attacks.",
            "It may cause stomach irritation or bleeding. Rarely, allergic reactions can happen.",
        ),
        (
            ["aspocid"],
            "This medicine thins your blood to prevent heart attacks or strokes. It keeps your blood flowing smoothly.",
            "It can cause easy bruising or bleeding. Some people may feel stomach discomfort.",
        ),
        (
            ["aspril"],
            "This medicine helps control high blood pressure and supports heart health. It makes your heart work more efficiently.",
            "It may cause dizziness or lightheadedness. Some people may develop a dry cough.",
        ),
        (
            ["axcer", "omeprazole", "pan", "pantocid", "pantop", "pantoprazole", "rabon-d"],
            "This medicine reduces stomach acid and helps treat heartburn, acidity, or ulcers.",
            "It may cause headache or diarrhea. Rarely, long-term use can affect vitamin levels.",
        ),
        (
            ["azee", "azithromycin", "aztar"],
            "This antibiotic treats bacterial infections like chest infections or skin infections. It helps your body fight harmful germs.",
            "Some people may get diarrhea or nausea. Rarely, allergic reactions can occur.",
        ),
        (
            ["becomin", "zincovit"],
            "This is a vitamin supplement that improves general health and immunity. It provides important nutrients your body needs.",
            "Some people may feel mild stomach upset. Rarely, an allergic reaction may happen.",
        ),
        (
            ["belladonna"],
            "This medicine helps reduce stomach cramps or abdominal pain. It relaxes the muscles in your gut.",
            "It may cause dry mouth or blurred vision. Some people feel drowsy or dizzy.",
        ),
        (
            ["biozil"],
            "This antibiotic treats bacterial infections in the body. It helps your immune system fight germs.",
            "It can cause nausea or mild stomach upset. Rarely, it may cause a skin rash.",
        ),
        (
            ["breese"],
            "This medicine helps relieve breathing problems like cough or mild asthma symptoms.",
            "Some people may feel headache or tremors. Rarely, it may cause dizziness.",
        ),
        (
            ["brinzox", "combigan"],
            "These eye drops reduce eye pressure in conditions like glaucoma. They help protect your eyesight.",
            "They may cause eye irritation or blurred vision. Rarely, some people feel a headache.",
        ),
        (
            ["cali-d", "d-fill"],
            "This supplement provides calcium or vitamin D for strong bones and healthy immunity.",
            "Some people may feel constipation or mild stomach upset. Rarely, high calcium levels or kidney stones can occur.",
        ),
        (
            ["carticare"],
            "This medicine supports joint health and reduces stiffness in arthritis.",
            "It may cause mild stomach upset. Some people feel nausea or diarrhea.",
        ),
        (
            ["cefixime", "ceptas", "omcef", "zyncep"],
            "This antibiotic treats bacterial infections like throat or urinary infections. It helps kill harmful bacteria in your body.",
            "It can cause diarrhea or stomach upset. Rarely, it may cause a rash.",
        ),
        (
            ["ceftas"],
            "This antibiotic treats more severe infections like pneumonia or skin infections.",
            "Injection site pain may occur. Some people get diarrhea or allergic reactions.",
        ),
        (
            ["cital"],
            "This medicine treats depression and helps improve mood.",
            "It may cause nausea or trouble sleeping. Some people feel dizziness.",
        ),
        (
            ["clopilet", "deplatt"],
            "This medicine prevents blood clots and reduces the risk of heart attacks or strokes.",
            "It can cause easy bruising or bleeding. Some people feel stomach discomfort.",
        ),
        (
            ["concor", "xstan-beta"],
            "This medicine controls high blood pressure and helps the heart beat more steadily.",
            "It may cause tiredness or fatigue. Some people feel a slow heartbeat or dizziness.",
        ),
        (
            ["diclofenac"],
            "This medicine reduces pain, swelling, and inflammation in joints or muscles.",
            "It may cause stomach irritation or heartburn. Some people can have kidney problems.",
        ),
        (
            ["dolostat", "dolostat-mr", "dolostat-pc"],
            "This medicine relieves pain, especially in muscles or arthritis.",
            "It may cause stomach upset or acidity. Some people feel drowsy.",
        ),
        (
            ["dom-dt", "domstall-dt", "domstat"],
            "This medicine reduces nausea and vomiting. It helps the stomach move food normally.",
            "It can cause dry mouth or dizziness. Rarely, heart rhythm changes may occur.",
        ),
        (
            ["doxy"],
            "This antibiotic treats bacterial infections like chest or skin infections.",
            "It may make your skin sensitive to sunlight. Some people feel nausea or diarrhea.",
        ),
        (
            ["filfresh"],
            "This supplement supports fertility and reproductive health.",
            "Some people may feel headache or mood changes. Rarely, nausea occurs.",
        ),
        (
            ["gemcel"],
            "This medicine supports nerve health, especially in diabetes or vitamin deficiencies.",
            "Some people feel mild stomach upset. Rarely, dizziness may occur.",
        ),
        (
            ["glimepiride", "zuylin"],
            "This medicine lowers blood sugar in people with diabetes.",
            "It can cause low blood sugar. Some people may feel nausea or dizziness.",
        ),
        (
            ["glycomet", "glycomet-gp1", "metformin"],
            "This medicine helps control blood sugar in people with diabetes.",
            "It may cause stomach upset or diarrhea. Rarely, low blood sugar or vitamin B12 deficiency can occur.",
        ),
        (
            ["happy"],
            "This medicine helps reduce anxiety and improves mood.",
            "It may cause drowsiness or dry mouth. Some people feel tired.",
        ),
        (
            ["ibuprofen"],
            "This medicine reduces pain, fever, and inflammation.",
            "It may cause stomach irritation. Rarely, it can affect the kidneys.",
        ),
        (
            ["k-stat", "kstart"],
            "This medicine helps prevent kidney stones and improve urinary health.",
            "Some people may feel stomach upset or nausea. Rarely, headaches may occur.",
        ),
        (
            ["ketaxol", "ketmol"],
            "This medicine relieves mild to moderate pain.",
            "It may cause drowsiness or nausea. Some people feel dizziness.",
        ),
        (
            ["ketorol"],
            "This medicine reduces severe pain, often after surgery or injury.",
            "It can irritate the stomach or cause nausea. Rarely, it affects the kidneys.",
        ),
        (
            ["leuco-x"],
            "This medicine helps increase white blood cells in people with low immunity.",
            "It may cause mild bone pain. Some people may feel fever or fatigue.",
        ),
        (
            ["levipil"],
            "This medicine helps control seizures in epilepsy.",
            "It may make you drowsy or tired. Some people feel mood changes.",
        ),
        (
            ["levipril", "losartan", "sartel"],
            "This medicine lowers high blood pressure and helps protect the heart and kidneys.",
            "It may cause dizziness or low blood pressure. Some people feel tired.",
        ),
        (
            ["levocetirizine"],
            "This medicine relieves allergy symptoms like sneezing, itchy nose, or itchy eyes.",
            "It may cause drowsiness. Some people feel dry mouth.",
        ),
        (
            ["linaglip"],
            "This medicine helps lower blood sugar in people with diabetes.",
            "It may cause low blood sugar or mild nausea. Some people may feel headache.",
        ),
        (
            ["lomotil"],
            "This medicine treats diarrhea and helps slow down bowel movements.",
            "It may cause constipation. Some people feel dizziness or drowsiness.",
        ),
        (
            ["lysatomep", "lysatone-plus", "ovicel"],
            "This supplement provides vitamins and minerals to support overall health and immunity.",
            "Some people may feel mild stomach upset. Rarely, allergic reactions can occur.",
        ),
        (
            ["meftal", "meftal-spas"],
            "This medicine relieves pain, especially abdominal cramps or muscle pain.",
            "It may cause dizziness or nausea. Some people have stomach upset.",
        ),
        (
            ["melonin"],
            "This supplement supports skin health and works as an antioxidant.",
            "Rarely, some people may experience mild allergic reactions.",
        ),
        (
            ["monef-gtm", "monit-gtn", "ranozex"],
            "This medicine helps with chest pain or angina by improving blood flow to the heart.",
            "It may cause headache or low blood pressure. Some people feel dizziness or constipation.",
        ),
        (
            ["montec1-lc", "montek", "monticope"],
            "This medicine helps with allergies and asthma symptoms.",
            "It may cause headache. Rarely, mood changes occur.",
        ),
        (
            ["neome-gl", "neomergl"],
            "This medicine helps control blood sugar and supports nerve health.",
            "It may cause stomach upset or mild nausea. Rarely, dizziness may occur.",
        ),
        (
            ["oligel", "relaxyl"],
            "This medicine helps reduce pain and swelling in muscles or joints.",
            "Some people may feel skin irritation, redness, drowsiness, or dizziness.",
        ),
        (
            ["opox", "opox-cv"],
            "This antibiotic treats bacterial infections in the body.",
            "It may cause stomach upset or diarrhea. Rarely, allergic reactions occur.",
        ),
        (
            ["pacimol", "pacimol-mf", "paracetamol"],
            "This medicine reduces fever and relieves mild pain.",
            "High doses can harm the liver. Some people may feel nausea.",
        ),
        (
            ["perfisca"],
            "This medicine relieves mild pain and inflammation.",
            "It may cause stomach upset. Rarely, dizziness occurs.",
        ),
        (
            ["prd", "r-rd"],
            "This medicine helps reduce pain and inflammation.",
            "It may cause drowsiness or stomach upset. Rarely, nausea occurs.",
        ),
        (
            ["rebs"],
            "This medicine helps with symptoms of irritable bowel syndrome like diarrhea.",
            "It may cause nausea or constipation. Rarely, stomach pain occurs.",
        ),
        (
            ["redotil"],
            "This medicine treats acute diarrhea and helps normalize bowel movements.",
            "It may cause headache or mild stomach upset. Rarely, allergic reactions happen.",
        ),
        (
            ["restil"],
            "This medicine helps reduce anxiety and improves sleep.",
            "It may cause sedation or drowsiness. Long-term use may cause dependence.",
        ),
        (
            ["seviste"],
            "This medicine helps with infections and respiratory problems.",
            "It may cause nausea or dizziness. Rarely, allergic reactions occur.",
        ),
        (
            ["shipan"],
            "This medicine helps digestion by providing digestive enzymes.",
            "It may cause mild stomach upset. Rarely, diarrhea occurs.",
        ),
        (
            ["thyrox"],
            "This medicine treats an underactive thyroid and helps regulate body metabolism.",
            "Taking too much may cause palpitations or weight loss. Some people feel anxiety.",
        ),
        (
            ["tibonor"],
            "This medicine helps with bone health and menopause symptoms.",
            "It may cause weight changes or mood swings. Rarely, headache occurs.",
        ),
        (
            ["vizylac"],
            "This is a probiotic that improves gut health and digestion.",
            "Some people may feel bloating or mild stomach upset. Rarely, nausea occurs.",
        ),
    ]

    fallback_map = {}
    for names, uses, side_effects in groups:
        entry = {"uses": uses, "side_effects": side_effects}
        for name in names:
            fallback_map[normalize_reference_key(name)] = entry
    return fallback_map


REFERENCE_FALLBACKS = load_reference_fallbacks_from_info() or build_reference_fallbacks()


def get_fallback_reference_info(medicine_name):
    entry = REFERENCE_FALLBACKS.get(normalize_reference_key(medicine_name))
    if not entry:
        return build_reference_info()
    return build_reference_info(entry["uses"], entry["side_effects"])


def resolve_reference_info(medicine_name, preferred_info=None, existing_info=None):
    fallback_info = get_fallback_reference_info(medicine_name)
    uses = ""
    side_effects = ""
    normalized_name = normalize_medicine_name(medicine_name, fuzzy_threshold=100)
    if normalized_name in KNOWN_MEDICINES:
        sources = (fallback_info, existing_info, preferred_info)
    else:
        sources = (preferred_info, existing_info, fallback_info)

    for info in sources:
        if not isinstance(info, dict):
            continue
        if not uses:
            uses = (info.get("uses") or "").strip()
        if not side_effects:
            side_effects = (info.get("side_effects") or "").strip()

    return build_reference_info(uses, side_effects)


def is_prefix(text):
    normalized_prefixes = [prefix.rstrip(".") for prefix in MEDICINE_PREFIXES]
    return text.lower().strip().rstrip(".") in normalized_prefixes


def is_dosage(text):
    import re

    patterns = [
        r"\d+mg",
        r"\d+ml",
        r"\d+-\d+-\d+",
        r"\b(od|bd|tds|qid|sos)\b",
        r"^\d+$",
    ]
    return any(re.search(pattern, text.lower()) for pattern in patterns)


def recognize(crop_pil):
    pixel_values = processor(
        crop_pil.convert("RGB"),
        return_tensors="pt",
    ).pixel_values
    if torch.cuda.is_available():
        pixel_values = pixel_values.cuda()
    with torch.no_grad():
        output = model.generate(pixel_values, max_new_tokens=32)
    return processor.batch_decode(output, skip_special_tokens=True)[0].strip().lower()


def get_drug_info(medicine_name):
    try:
        url = (
            "https://api.fda.gov/drug/label.json"
            f"?search=openfda.brand_name:{medicine_name}&limit=1"
        )
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                result = data["results"][0]
                return {
                    "found": True,
                    "brand_name": result.get("openfda", {}).get("brand_name", ["N/A"])[0],
                    "generic_name": result.get("openfda", {}).get("generic_name", ["N/A"])[0],
                    "purpose": (
                        result.get("purpose", ["N/A"])[0][:200]
                        if result.get("purpose")
                        else "N/A"
                    ),
                    "warnings": (
                        result.get("warnings", ["N/A"])[0][:200]
                        if result.get("warnings")
                        else "N/A"
                    ),
                }
    except Exception:
        pass
    return {"found": False}


def group_easyocr_lines(sorted_results, y_tolerance=20):
    lines = []
    for bbox, text, conf in sorted_results:
        y_center = sum(point[1] for point in bbox) / len(bbox)
        x_left = min(point[0] for point in bbox)

        if not lines or abs(y_center - lines[-1]["y_center"]) > y_tolerance:
            lines.append({"y_center": y_center, "tokens": [(x_left, text)]})
        else:
            lines[-1]["tokens"].append((x_left, text))

    grouped = []
    for line in lines:
        ordered_tokens = [text for _, text in sorted(line["tokens"], key=lambda item: item[0])]
        grouped.append(" ".join(ordered_tokens))
    return grouped


def detect_medicine_regions(img, sorted_results):
    medicine_regions = []

    for i, (bbox, text, conf) in enumerate(sorted_results):
        if not is_prefix(text):
            continue

        y1_current = min(point[1] for point in bbox)
        y2_current = max(point[1] for point in bbox)
        x1_current = min(point[0] for point in bbox)

        for bbox2, text2, conf2 in sorted_results[i + 1 :]:
            x1_next = min(point[0] for point in bbox2)
            y1_next = min(point[1] for point in bbox2)
            y2_next = max(point[1] for point in bbox2)
            overlap = min(y2_current, y2_next) - max(y1_current, y1_next)
            height = max(y2_current - y1_current, y2_next - y1_next)

            if overlap > height * 0.3 and x1_next > x1_current and not is_dosage(text2):
                x1 = max(0, int(min(point[0] for point in bbox2)) - 4)
                y1 = max(0, int(min(point[1] for point in bbox2)) - 4)
                x2 = min(img.width, int(max(point[0] for point in bbox2)) + 4)
                y2 = min(img.height, int(max(point[1] for point in bbox2)) + 4)
                medicine_regions.append(
                    {
                        "bbox": (x1, y1, x2, y2),
                        "easy_text": text2,
                        "prefix": text,
                    }
                )
                break

    if not medicine_regions:
        for bbox, text, conf in sorted_results:
            if len(text) > 3 and not is_dosage(text) and not is_prefix(text):
                x1 = max(0, int(min(point[0] for point in bbox)) - 4)
                y1 = max(0, int(min(point[1] for point in bbox)) - 4)
                x2 = min(img.width, int(max(point[0] for point in bbox)) + 4)
                y2 = min(img.height, int(max(point[1] for point in bbox)) + 4)
                medicine_regions.append(
                    {
                        "bbox": (x1, y1, x2, y2),
                        "easy_text": text,
                        "prefix": "?",
                    }
                )

    return medicine_regions


def normalize_medicine_name(name, fuzzy_threshold=88):
    cleaned = (name or "").strip().lower()
    if not cleaned:
        return ""

    if cleaned in KNOWN_MEDICINES:
        return cleaned

    corrected_name, score, status = correct(cleaned, threshold_accept=fuzzy_threshold, threshold_uncertain=0)
    if corrected_name and score >= fuzzy_threshold:
        return corrected_name

    return cleaned


def build_gemini_image_bytes(image, max_size=(1600, 1600)):
    resized = image.copy()
    resized.thumbnail(max_size)
    buffer = io.BytesIO()
    resized.save(buffer, format="PNG")
    return buffer.getvalue()


def build_buy_links(medicine_name):
    search_targets = [
        ("Tata 1mg", "www.1mg.com"),
        ("Apollo Pharmacy", "www.apollopharmacy.in"),
        ("PharmEasy", "pharmeasy.in"),
    ]
    return [
        {
            "label": label,
            "url": f"https://www.google.com/search?q={quote_plus(f'{medicine_name} site:{domain}')}",
        }
        for label, domain in search_targets
    ]


def parse_float(value, field_name):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a number")
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be a valid number")
    return number


def haversine_distance_m(lat1, lon1, lat2, lon2):
    radius_m = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius_m * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_pharmacy_address(tags):
    address_parts = []
    for key in ("addr:housenumber", "addr:street", "addr:suburb", "addr:city", "addr:postcode"):
        value = (tags.get(key) or "").strip()
        if value and value not in address_parts:
            address_parts.append(value)
    return ", ".join(address_parts)


def extract_local_medicines(img, medicine_regions):
    medicines = []
    trocr_reads = []
    easy_hints = []
    seen = set()

    for region in medicine_regions:
        crop = img.crop(region["bbox"])
        raw = recognize(crop)
        trocr_reads.append(raw)
        easy_hints.append(region["easy_text"])
        corrected, score, status = correct(raw)

        if corrected in seen:
            continue

        seen.add(corrected)
        medicines.append(
            {
                "prefix": region["prefix"],
                "easy_ocr": region["easy_text"],
                "raw_ocr": raw,
                "corrected": corrected,
                "confidence": round(score, 1),
                "status": status,
                "reference_info": get_fallback_reference_info(corrected),
                "buy_links": build_buy_links(corrected),
            }
        )

    return medicines, trocr_reads, easy_hints


def build_gemini_prompt(easyocr_lines, easy_hints, trocr_reads):
    easy_lines_text = "\n".join(f"- {line}" for line in easyocr_lines[:40]) or "- none"
    easy_hints_text = "\n".join(f"- {hint}" for hint in easy_hints[:20]) or "- none"
    trocr_text = "\n".join(f"- {text}" for text in trocr_reads[:20]) or "- none"
    medicine_text = ", ".join(KNOWN_MEDICINES)

    return f"""
You are extracting medicine names from a handwritten prescription image.

Important rules:
- Use the attached prescription image as the primary source.
- EasyOCR and TrOCR text are only hints and may contain mistakes.
- Return only medicine names, not dosage, schedule, quantity, or instructions.
- Prefer normalized names from the known medicine list when there is a close match.
- Remove duplicates.
- If you are unsure, keep only high-probability medicine names.
- For medicines from the known medicine list, leave uses and side_effects empty because the app has local reference notes.
- For medicines outside the known medicine list, provide a short common uses summary and a short common side-effects summary.
- Keep uses and side effects concise and factual.

Known medicine list:
{medicine_text}

EasyOCR full-text lines:
{easy_lines_text}

EasyOCR medicine hints:
{easy_hints_text}

TrOCR region reads:
{trocr_text}
""".strip()


def extract_response_text(response_json):
    candidates = response_json.get("candidates", [])
    if not candidates:
        return ""

    parts = candidates[0].get("content", {}).get("parts", [])
    texts = [part.get("text", "") for part in parts if part.get("text")]
    return "".join(texts).strip()


def call_gemini_for_medicines(image_bytes, easyocr_lines, easy_hints, trocr_reads):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing")

    prompt = build_gemini_prompt(easyocr_lines, easy_hints, trocr_reads)
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": base64.b64encode(image_bytes).decode("utf-8"),
                        }
                    },
                    {"text": prompt},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "medicines": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "name": {"type": "STRING"},
                                "uses": {"type": "STRING"},
                                "side_effects": {"type": "STRING"},
                            },
                            "required": ["name", "uses", "side_effects"],
                        },
                    }
                },
                "required": ["medicines"],
            },
        },
    }

    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        params={"key": api_key},
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Gemini request failed with status {response.status_code}")

    response_json = response.json()
    response_text = extract_response_text(response_json)
    if not response_text:
        raise RuntimeError("Gemini returned an empty response")

    parsed = json.loads(response_text)
    raw_medicines = parsed.get("medicines", [])
    if not isinstance(raw_medicines, list):
        raise RuntimeError("Gemini returned an invalid medicines list")

    normalized = []
    seen = set()
    for medicine in raw_medicines:
        if not isinstance(medicine, dict):
            continue
        normalized_name = normalize_medicine_name(medicine.get("name", ""))
        if not normalized_name or normalized_name in seen:
            continue
        seen.add(normalized_name)
        normalized.append(
            {
                "name": normalized_name,
                "uses": medicine.get("uses", "").strip(),
                "side_effects": medicine.get("side_effects", "").strip(),
            }
        )

    return normalized


def build_ai_medicine_results(medicine_items):
    results = []
    for medicine in medicine_items:
        medicine_name = medicine["name"]
        results.append(
            {
                "prefix": "",
                "easy_ocr": "",
                "raw_ocr": "",
                "corrected": medicine_name,
                "confidence": None,
                "status": "extracted",
                "badge_text": "Whole-image AI",
                "badge_class": "badge-green",
                "detail_note": "",
                "reference_info": resolve_reference_info(medicine_name, preferred_info=medicine),
                "buy_links": build_buy_links(medicine_name),
            }
        )
    return results


def merge_medicine_results(local_medicines, gemini_medicine_items):
    merged = []
    seen = set()
    gemini_map = {
        normalize_medicine_name(medicine["name"], fuzzy_threshold=100): medicine
        for medicine in gemini_medicine_items
        if medicine.get("name")
    }

    for medicine in local_medicines:
        normalized_name = normalize_medicine_name(medicine.get("corrected", ""), fuzzy_threshold=100)
        medicine_copy = dict(medicine)
        gemini_match = gemini_map.get(normalized_name)
        if gemini_match:
            medicine_copy["detail_note"] = "Also confirmed by the whole-image AI pass."
        medicine_copy["reference_info"] = resolve_reference_info(
            medicine_copy.get("corrected", ""),
            preferred_info=gemini_match,
            existing_info=medicine_copy.get("reference_info"),
        )
        merged.append(medicine_copy)
        seen.add(normalized_name)

    gemini_only = [
        medicine
        for medicine in gemini_medicine_items
        if normalize_medicine_name(medicine["name"], fuzzy_threshold=100) not in seen
    ]
    merged.extend(build_ai_medicine_results(gemini_only))
    return merged


def call_gemini_for_reference_translation(items, target_language):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing")

    prompt = (
        f"Translate the uses and side_effects fields into {target_language}. "
        "Keep each medicine name unchanged. Keep the same order. "
        "Use concise natural language for patients in India. "
        "Return strict JSON only."
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"text": json.dumps({"items": items}, ensure_ascii=False)},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "items": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "name": {"type": "STRING"},
                                "uses": {"type": "STRING"},
                                "side_effects": {"type": "STRING"},
                            },
                            "required": ["name", "uses", "side_effects"],
                        },
                    }
                },
                "required": ["items"],
            },
        },
    }

    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        params={"key": api_key},
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Gemini translation failed with status {response.status_code}")

    response_json = response.json()
    response_text = extract_response_text(response_json)
    if not response_text:
        raise RuntimeError("Gemini translation returned an empty response")

    parsed = json.loads(response_text)
    translated_items = parsed.get("items", [])
    if not isinstance(translated_items, list):
        raise RuntimeError("Gemini translation returned an invalid items list")

    normalized = []
    for item in translated_items:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "name": normalize_medicine_name(item.get("name", ""), fuzzy_threshold=100),
                "uses": item.get("uses", "").strip(),
                "side_effects": item.get("side_effects", "").strip(),
            }
        )
    return normalized


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return Response(status=204)


@app.route("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools_manifest():
    return jsonify({})


@app.route("/process", methods=["POST"])
def process():
    if "image" not in request.files:
        return jsonify({"error": "No image"}), 400

    file = request.files["image"]
    img = Image.open(file.stream).convert("RGB")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        img.save(temp_path, format="PNG")
        results = reader.readtext(temp_path)
        image_bytes = build_gemini_image_bytes(img)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    sorted_results = sorted(
        results,
        key=lambda item: (min(point[1] for point in item[0]), min(point[0] for point in item[0])),
    )
    easyocr_lines = group_easyocr_lines(sorted_results)
    medicine_regions = detect_medicine_regions(img, sorted_results)
    local_medicines, trocr_reads, easy_hints = extract_local_medicines(img, medicine_regions)

    medicines = local_medicines
    engine = "local_ocr"
    gemini_error = ""

    try:
        gemini_medicines = call_gemini_for_medicines(
            image_bytes=image_bytes,
            easyocr_lines=easyocr_lines,
            easy_hints=easy_hints,
            trocr_reads=trocr_reads,
        )
        if gemini_medicines:
            medicines = merge_medicine_results(local_medicines, gemini_medicines)
            engine = "hybrid_ocr"
    except Exception as exc:
        gemini_error = str(exc)

    return jsonify(
        {
            "medicines": medicines,
            "total": len(medicines),
            "engine": engine,
            "gemini_error": gemini_error,
        }
    )


@app.route("/translate_references", methods=["POST"])
def translate_references():
    payload = request.get_json(silent=True) or {}
    items = payload.get("items", [])
    target_language = (payload.get("target_language") or "").strip()

    if not items:
        return jsonify({"error": "No items to translate"}), 400
    if not target_language:
        return jsonify({"error": "No target language provided"}), 400
    if target_language.lower() == "english":
        return jsonify({"items": items, "target_language": "English"})

    translated_items = call_gemini_for_reference_translation(items, target_language)
    return jsonify({"items": translated_items, "target_language": target_language})


@app.route("/nearby_pharmacies", methods=["POST"])
def nearby_pharmacies():
    payload = request.get_json(silent=True) or {}
    try:
        lat = parse_float(payload.get("lat"), "lat")
        lon = parse_float(payload.get("lon"), "lon")
        radius_m = int(payload.get("radius_m") or 2000)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        return jsonify({"error": "Location is outside valid latitude/longitude bounds"}), 400

    radius_m = max(100, min(radius_m, 10000))
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="pharmacy"](around:{radius_m},{lat},{lon});
      way["amenity"="pharmacy"](around:{radius_m},{lat},{lon});
      relation["amenity"="pharmacy"](around:{radius_m},{lat},{lon});
      node["shop"="chemist"](around:{radius_m},{lat},{lon});
      way["shop"="chemist"](around:{radius_m},{lat},{lon});
      relation["shop"="chemist"](around:{radius_m},{lat},{lon});
      node["healthcare"="pharmacy"](around:{radius_m},{lat},{lon});
      way["healthcare"="pharmacy"](around:{radius_m},{lat},{lon});
      relation["healthcare"="pharmacy"](around:{radius_m},{lat},{lon});
    );
    out center tags;
    """.strip()

    try:
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": overpass_query},
            headers={"User-Agent": "PrescriptionOCR/1.0"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        return jsonify({"error": f"Nearby pharmacy search failed: {exc}"}), 502

    pharmacies = []
    seen = set()
    for element in data.get("elements", []):
        tags = element.get("tags") or {}
        element_lat = element.get("lat")
        element_lon = element.get("lon")
        if element_lat is None or element_lon is None:
            center = element.get("center") or {}
            element_lat = center.get("lat")
            element_lon = center.get("lon")
        if element_lat is None or element_lon is None:
            continue

        pharmacy_id = f"{element.get('type', 'item')}/{element.get('id')}"
        if pharmacy_id in seen:
            continue
        seen.add(pharmacy_id)

        distance_m = haversine_distance_m(lat, lon, float(element_lat), float(element_lon))
        pharmacies.append(
            {
                "id": pharmacy_id,
                "name": tags.get("name") or "Medical store",
                "lat": float(element_lat),
                "lon": float(element_lon),
                "address": build_pharmacy_address(tags),
                "distance_m": round(distance_m),
                "tags": tags,
            }
        )

    pharmacies.sort(key=lambda pharmacy: pharmacy["distance_m"])
    return jsonify({"pharmacies": pharmacies[:25], "radius_m": radius_m})


@app.route("/route_to_pharmacy", methods=["POST"])
def route_to_pharmacy():
    payload = request.get_json(silent=True) or {}
    start = payload.get("start") or {}
    end = payload.get("end") or {}

    try:
        start_lat = parse_float(start.get("lat"), "start.lat")
        start_lon = parse_float(start.get("lon"), "start.lon")
        end_lat = parse_float(end.get("lat"), "end.lat")
        end_lon = parse_float(end.get("lon"), "end.lon")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    for label, lat, lon in (
        ("start", start_lat, start_lon),
        ("end", end_lat, end_lon),
    ):
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            return jsonify({"error": f"{label} is outside valid latitude/longitude bounds"}), 400

    coordinates = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    try:
        response = requests.get(
            f"https://router.project-osrm.org/route/v1/driving/{coordinates}",
            params={"overview": "full", "geometries": "geojson"},
            headers={"User-Agent": "PrescriptionOCR/1.0"},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        routes = data.get("routes") or []
        if not routes:
            return jsonify({"error": "No route found to the selected medical store"}), 502
        route = routes[0]
    except Exception as exc:
        return jsonify({"error": f"Route search failed: {exc}"}), 502

    return jsonify(
        {
            "distance_m": route.get("distance"),
            "duration_s": route.get("duration"),
            "geometry": route.get("geometry"),
        }
    )


HTML = '''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Prescription OCR</title>
<link rel="icon" href="data:,">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui; background: #f0f4f8; color: #333; }
.container { max-width: 900px; margin: 0 auto; padding: 20px; }
h1 { color: #1a73e8; text-align: center; margin-bottom: 8px; }
.subtitle { text-align: center; color: #666; margin-bottom: 30px; }
.card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}
.step-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.step-num {
  background: #1a73e8;
  color: white;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  flex-shrink: 0;
}
.step-title { font-size: 18px; font-weight: 600; }
.upload-area {
  border: 2px dashed #1a73e8;
  border-radius: 8px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: background 0.2s;
}
.upload-area:hover { background: #e8f0fe; }
.crop-workspace { display: none; margin-top: 18px; }
.crop-stage {
  position: relative;
  display: inline-block;
  max-width: 100%;
  border-radius: 12px;
  overflow: hidden;
  background: #dfe7f3;
}
#preview {
  display: block;
  max-width: 100%;
  max-height: 70vh;
  border-radius: 12px;
}
.crop-box {
  position: absolute;
  border: 2px solid #1a73e8;
  border-radius: 12px;
  box-shadow: 0 0 0 9999px rgba(15, 23, 42, 0.35);
  cursor: move;
  touch-action: none;
}
.crop-handle {
  position: absolute;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #1a73e8;
}
.crop-handle[data-handle="nw"] { top: -8px; left: -8px; cursor: nwse-resize; }
.crop-handle[data-handle="ne"] { top: -8px; right: -8px; cursor: nesw-resize; }
.crop-handle[data-handle="sw"] { bottom: -8px; left: -8px; cursor: nesw-resize; }
.crop-handle[data-handle="se"] { bottom: -8px; right: -8px; cursor: nwse-resize; }
.crop-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 14px;
}
.crop-help { color: #666; font-size: 13px; }
.btn {
  background: #1a73e8;
  color: white;
  border: none;
  padding: 12px 28px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  transition: background 0.2s;
}
.btn:hover { background: #1557b0; }
.btn:disabled { background: #aaa; cursor: not-allowed; }
.btn-secondary {
  background: #eef3fb;
  color: #1a73e8;
  border: 1px solid #c9d8f0;
}
.btn-secondary:hover { background: #dfeafc; }
.medicine-card { border: 1px solid #e0e0e0; border-radius: 10px; padding: 16px; margin-bottom: 12px; }
.medicine-name { font-size: 20px; font-weight: 700; color: #1a73e8; }
.medicine-subtitle { margin-top: 6px; color: #666; font-size: 13px; }
.info-section {
  margin-top: 12px;
  padding: 14px;
  background: #f4f7ff;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.5;
}
.info-title { font-weight: 600; color: #1557b0; margin-bottom: 6px; }
.info-muted { color: #6b7280; }
.buy-links {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.buy-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  padding: 9px 14px;
  border-radius: 999px;
  border: 1px solid #c9d8f0;
  background: #fff;
  color: #1a73e8;
  font-size: 13px;
  font-weight: 600;
}
.buy-link:hover { background: #eff5ff; }
.translation-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
  align-items: center;
}
.translation-label { color: #4b5563; font-size: 14px; font-weight: 600; }
.lang-btn {
  border: 1px solid #c9d8f0;
  background: #fff;
  color: #1a73e8;
  border-radius: 999px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}
.lang-btn.active {
  background: #1a73e8;
  color: #fff;
  border-color: #1a73e8;
}
.loading { text-align: center; padding: 40px; color: #666; display: none; }
.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e0e0e0;
  border-top: 4px solid #1a73e8;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.summary-box { background: #e8f0fe; border-radius: 8px; padding: 16px; text-align: center; }
.summary-num { font-size: 48px; font-weight: 700; color: #1a73e8; }
.copy-btn {
  background: #fff;
  color: #1a73e8;
  border: 2px solid #1a73e8;
  padding: 8px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  margin-top: 12px;
}
.results-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.status-text {
  margin-top: 12px;
  color: #4b5563;
  font-size: 14px;
}
.status-error { color: #b42318; }
.map-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
  gap: 16px;
  margin-top: 16px;
}
#pharmacyMap {
  min-height: 360px;
  border: 1px solid #d5deeb;
  border-radius: 8px;
  background: #edf2f7;
}
.pharmacy-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 360px;
  overflow: auto;
}
.pharmacy-item {
  border: 1px solid #d5deeb;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}
.pharmacy-name { font-weight: 700; color: #1f2937; }
.pharmacy-meta { margin-top: 5px; color: #6b7280; font-size: 13px; line-height: 1.4; }
.route-summary {
  margin-top: 12px;
  padding: 12px;
  border-radius: 8px;
  background: #edf7ed;
  color: #1b5e20;
  font-size: 14px;
  font-weight: 600;
}
@media (max-width: 760px) {
  .map-layout { grid-template-columns: 1fr; }
}
</style>
</head>
<body>
<div class="container">
  <h1>Prescription OCR</h1>
  <p class="subtitle">Upload a handwritten prescription, crop the relevant medicine area, and extract medicine names with short reference notes.</p>

  <div class="card">
    <div class="step-header">
      <div class="step-num">1</div>
      <div class="step-title">Upload And Crop</div>
    </div>
    <div class="upload-area" onclick="document.getElementById('fileInput').click()">
      <div style="font-size: 48px">+</div>
      <p style="margin-top: 8px; color: #666">Click to upload a prescription image</p>
      <p style="font-size: 12px; color: #aaa; margin-top: 4px">After upload, drag the crop box and resize it from the corners.</p>
    </div>
    <input type="file" id="fileInput" accept="image/*" style="display:none">
    <div class="crop-workspace" id="cropWorkspace">
      <div class="crop-stage" id="cropStage">
        <img id="preview" alt="Prescription preview">
        <div class="crop-box" id="cropBox">
          <div class="crop-handle" data-handle="nw"></div>
          <div class="crop-handle" data-handle="ne"></div>
          <div class="crop-handle" data-handle="sw"></div>
          <div class="crop-handle" data-handle="se"></div>
        </div>
      </div>
      <div class="crop-toolbar">
        <button class="btn btn-secondary" type="button" onclick="resetCrop()">Reset Crop</button>
        <span class="crop-help">Move the blue box or drag its corners to keep only the useful part of the prescription.</span>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="step-header">
      <div class="step-num">2</div>
      <div class="step-title">Extract Medicines</div>
    </div>
    <p style="color: #666; margin-bottom: 16px">
      The cropped image goes to OCR first, then Gemini combines the image with EasyOCR and TrOCR hints to return medicine names, uses, and side effects.
    </p>
    <button class="btn" id="extractBtn" onclick="extract()" disabled>
      Extract Medicines
    </button>
  </div>

  <div class="loading" id="loading">
    <div class="spinner"></div>
    <p>Processing prescription...<br>
    <small>Reading the cropped image, extracting medicines, and preparing reference notes</small></p>
  </div>

  <div class="card" id="resultsCard" style="display:none">
    <div class="step-header">
      <div class="step-num">3</div>
      <div class="step-title">Results</div>
    </div>
    <div class="summary-box" id="summaryBox"></div>
    <div class="translation-toolbar" id="translationToolbar" style="display:none">
      <span class="translation-label">Translate:</span>
      <button class="lang-btn active" data-language="English" onclick="translateAll('English')">English</button>
      <button class="lang-btn" data-language="Assamese" onclick="translateAll('Assamese')">Assamese</button>
      <button class="lang-btn" data-language="Bengali" onclick="translateAll('Bengali')">Bengali</button>
      <button class="lang-btn" data-language="Bodo" onclick="translateAll('Bodo')">Bodo</button>
      <button class="lang-btn" data-language="Dogri" onclick="translateAll('Dogri')">Dogri</button>
      <button class="lang-btn" data-language="Gujarati" onclick="translateAll('Gujarati')">Gujarati</button>
      <button class="lang-btn" data-language="Hindi" onclick="translateAll('Hindi')">Hindi</button>
      <button class="lang-btn" data-language="Kannada" onclick="translateAll('Kannada')">Kannada</button>
      <button class="lang-btn" data-language="Kashmiri" onclick="translateAll('Kashmiri')">Kashmiri</button>
      <button class="lang-btn" data-language="Konkani" onclick="translateAll('Konkani')">Konkani</button>
      <button class="lang-btn" data-language="Maithili" onclick="translateAll('Maithili')">Maithili</button>
      <button class="lang-btn" data-language="Malayalam" onclick="translateAll('Malayalam')">Malayalam</button>
      <button class="lang-btn" data-language="Manipuri" onclick="translateAll('Manipuri')">Manipuri</button>
      <button class="lang-btn" data-language="Marathi" onclick="translateAll('Marathi')">Marathi</button>
      <button class="lang-btn" data-language="Nepali" onclick="translateAll('Nepali')">Nepali</button>
      <button class="lang-btn" data-language="Odia" onclick="translateAll('Odia')">Odia</button>
      <button class="lang-btn" data-language="Punjabi" onclick="translateAll('Punjabi')">Punjabi</button>
      <button class="lang-btn" data-language="Sanskrit" onclick="translateAll('Sanskrit')">Sanskrit</button>
      <button class="lang-btn" data-language="Santali" onclick="translateAll('Santali')">Santali</button>
      <button class="lang-btn" data-language="Sindhi" onclick="translateAll('Sindhi')">Sindhi</button>
      <button class="lang-btn" data-language="Telugu" onclick="translateAll('Telugu')">Telugu</button>
      <button class="lang-btn" data-language="Tamil" onclick="translateAll('Tamil')">Tamil</button>
      <button class="lang-btn" data-language="Urdu" onclick="translateAll('Urdu')">Urdu</button>
    </div>
    <div id="medicineList" style="margin-top: 20px"></div>
    <div class="results-actions">
      <button class="copy-btn" onclick="copyList()">Copy Medicine List</button>
      <button class="copy-btn" id="readAloudBtn" onclick="toggleReadAloud()">Read Aloud</button>
    </div>
  </div>

  <div class="card" id="pharmacyCard" style="display:none">
    <div class="step-header">
      <div class="step-num">4</div>
      <div class="step-title">Nearby Medical Stores</div>
    </div>
    <button class="btn" id="findPharmaciesBtn" onclick="findNearbyPharmacies()">Find Nearby Medical Stores</button>
    <div class="status-text" id="pharmacyStatus"></div>
    <div class="route-summary" id="routeSummary" style="display:none"></div>
    <div class="map-layout" id="mapLayout" style="display:none">
      <div id="pharmacyMap"></div>
      <div class="pharmacy-list" id="pharmacyList"></div>
    </div>
  </div>
</div>
<canvas id="cropCanvas" style="display:none"></canvas>

<script>
let selectedFile = null;
let cropRect = null;
let dragState = null;
let baseResults = null;
let currentResults = null;
let activeLanguage = 'English';
let userLocation = null;
let pharmacies = [];
let pharmacyMap = null;
let userMarker = null;
let pharmacyMarkers = [];
let routeLine = null;
let isSpeaking = false;

const preview = document.getElementById('preview');
const cropWorkspace = document.getElementById('cropWorkspace');
const cropStage = document.getElementById('cropStage');
const cropBox = document.getElementById('cropBox');
const cropCanvas = document.getElementById('cropCanvas');
const translationToolbar = document.getElementById('translationToolbar');
const languageButtons = Array.from(document.querySelectorAll('.lang-btn'));
const pharmacyCard = document.getElementById('pharmacyCard');
const pharmacyStatus = document.getElementById('pharmacyStatus');
const pharmacyList = document.getElementById('pharmacyList');
const mapLayout = document.getElementById('mapLayout');
const routeSummary = document.getElementById('routeSummary');
const findPharmaciesBtn = document.getElementById('findPharmaciesBtn');
const readAloudBtn = document.getElementById('readAloudBtn');

const languageVoiceHints = {
  English: 'en-IN',
  Assamese: 'as-IN',
  Bengali: 'bn-IN',
  Bodo: 'hi-IN',
  Dogri: 'hi-IN',
  Gujarati: 'gu-IN',
  Hindi: 'hi-IN',
  Kannada: 'kn-IN',
  Kashmiri: 'ur-IN',
  Konkani: 'hi-IN',
  Maithili: 'hi-IN',
  Malayalam: 'ml-IN',
  Manipuri: 'hi-IN',
  Marathi: 'mr-IN',
  Nepali: 'ne-NP',
  Odia: 'or-IN',
  Punjabi: 'pa-IN',
  Sanskrit: 'hi-IN',
  Santali: 'hi-IN',
  Sindhi: 'hi-IN',
  Tamil: 'ta-IN',
  Telugu: 'te-IN',
  Urdu: 'ur-IN',
};

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function escapeHtml(text) {
  return String(text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function initializeCrop() {
  const width = preview.clientWidth;
  const height = preview.clientHeight;
  if (!width || !height) return;

  cropRect = {
    x: width * 0.06,
    y: height * 0.08,
    width: width * 0.88,
    height: height * 0.84,
  };
  renderCropBox();
}

function renderCropBox() {
  if (!cropRect) return;
  cropBox.style.display = 'block';
  cropBox.style.left = `${cropRect.x}px`;
  cropBox.style.top = `${cropRect.y}px`;
  cropBox.style.width = `${cropRect.width}px`;
  cropBox.style.height = `${cropRect.height}px`;
}

function resetCrop() {
  initializeCrop();
}

function startDrag(mode, handle, event) {
  if (!cropRect) return;
  event.preventDefault();
  dragState = {
    mode,
    handle,
    startX: event.clientX,
    startY: event.clientY,
    rect: { ...cropRect },
    stageWidth: cropStage.clientWidth,
    stageHeight: cropStage.clientHeight,
  };
  window.addEventListener('pointermove', onPointerMove);
  window.addEventListener('pointerup', stopDrag);
}

function onPointerMove(event) {
  if (!dragState) return;

  const dx = event.clientX - dragState.startX;
  const dy = event.clientY - dragState.startY;
  const minSize = 48;

  if (dragState.mode === 'move') {
    cropRect = {
      ...cropRect,
      x: clamp(dragState.rect.x + dx, 0, dragState.stageWidth - dragState.rect.width),
      y: clamp(dragState.rect.y + dy, 0, dragState.stageHeight - dragState.rect.height),
    };
    renderCropBox();
    return;
  }

  let left = dragState.rect.x;
  let top = dragState.rect.y;
  let right = dragState.rect.x + dragState.rect.width;
  let bottom = dragState.rect.y + dragState.rect.height;

  if (dragState.handle.includes('w')) {
    left = clamp(dragState.rect.x + dx, 0, right - minSize);
  }
  if (dragState.handle.includes('e')) {
    right = clamp(dragState.rect.x + dragState.rect.width + dx, left + minSize, dragState.stageWidth);
  }
  if (dragState.handle.includes('n')) {
    top = clamp(dragState.rect.y + dy, 0, bottom - minSize);
  }
  if (dragState.handle.includes('s')) {
    bottom = clamp(dragState.rect.y + dragState.rect.height + dy, top + minSize, dragState.stageHeight);
  }

  cropRect = {
    x: left,
    y: top,
    width: right - left,
    height: bottom - top,
  };
  renderCropBox();
}

function stopDrag() {
  dragState = null;
  window.removeEventListener('pointermove', onPointerMove);
  window.removeEventListener('pointerup', stopDrag);
}

cropBox.addEventListener('pointerdown', function (event) {
  if (event.target.dataset.handle) return;
  startDrag('move', '', event);
});

document.querySelectorAll('.crop-handle').forEach((handle) => {
  handle.addEventListener('pointerdown', function (event) {
    event.stopPropagation();
    startDrag('resize', event.target.dataset.handle, event);
  });
});

document.getElementById('fileInput').addEventListener('change', function (event) {
  selectedFile = event.target.files[0];
  if (!selectedFile) return;

  const reader = new FileReader();
  reader.onload = function (loadEvent) {
    preview.onload = function () {
      cropWorkspace.style.display = 'block';
      initializeCrop();
    };
    preview.src = loadEvent.target.result;
  };
  reader.readAsDataURL(selectedFile);
  document.getElementById('extractBtn').disabled = false;
  document.getElementById('resultsCard').style.display = 'none';
  pharmacyCard.style.display = 'none';
  stopReadAloud();
});

async function getCroppedFile() {
  if (!selectedFile || !cropRect) return selectedFile;

  const scaleX = preview.naturalWidth / preview.clientWidth;
  const scaleY = preview.naturalHeight / preview.clientHeight;
  const sourceX = Math.round(cropRect.x * scaleX);
  const sourceY = Math.round(cropRect.y * scaleY);
  const sourceWidth = Math.round(cropRect.width * scaleX);
  const sourceHeight = Math.round(cropRect.height * scaleY);

  cropCanvas.width = sourceWidth;
  cropCanvas.height = sourceHeight;
  const context = cropCanvas.getContext('2d');
  context.clearRect(0, 0, cropCanvas.width, cropCanvas.height);
  context.drawImage(
    preview,
    sourceX,
    sourceY,
    sourceWidth,
    sourceHeight,
    0,
    0,
    cropCanvas.width,
    cropCanvas.height
  );

  return await new Promise((resolve, reject) => {
    cropCanvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error('Unable to crop image'));
        return;
      }
      resolve(new File([blob], 'cropped-prescription.png', { type: 'image/png' }));
    }, 'image/png');
  });
}

async function extract() {
  if (!selectedFile) return;

  document.getElementById('loading').style.display = 'block';
  document.getElementById('resultsCard').style.display = 'none';
  document.getElementById('extractBtn').disabled = true;

  try {
    const croppedFile = await getCroppedFile();
    const formData = new FormData();
    formData.append('image', croppedFile);

    const response = await fetch('/process', { method: 'POST', body: formData });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Error processing image');
    }

    displayResults(data);
  } catch (error) {
    alert('Error processing image: ' + error.message);
  } finally {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('extractBtn').disabled = false;
  }
}

function updateLanguageButtons(language) {
  languageButtons.forEach((button) => {
    button.classList.toggle('active', button.dataset.language === language);
  });
}

function displayResults(data) {
  baseResults = deepClone(data);
  currentResults = deepClone(data);
  activeLanguage = 'English';
  renderResults();
  pharmacyCard.style.display = 'block';
}

function renderResults() {
  const card = document.getElementById('resultsCard');
  const summary = document.getElementById('summaryBox');
  const list = document.getElementById('medicineList');
  const data = currentResults;
  if (!data) return;

  summary.innerHTML = `
    <div class="summary-num">${data.total}</div>
    <div style="color: #444; font-weight: 500">Medicines Found</div>
    <div style="margin-top:8px;color:#666;font-size:13px">Showing medicine names, short uses, side effects, and online pharmacy search links.</div>
    ${activeLanguage !== 'English' ? `<div style="margin-top:8px;color:#1557b0;font-size:13px;font-weight:600">Language: ${escapeHtml(activeLanguage)}</div>` : ''}
  `;

  const hasReferenceInfo = data.medicines.some((medicine) => medicine.reference_info && medicine.reference_info.found);
  translationToolbar.style.display = hasReferenceInfo ? 'flex' : 'none';
  updateLanguageButtons(activeLanguage);

  list.innerHTML = '';

  data.medicines.forEach((medicine, index) => {
    const referenceHtml = medicine.reference_info && medicine.reference_info.found
      ? `
        <div class="info-section">
          <div class="info-title">Reference Summary</div>
          <div><b>Uses:</b> ${escapeHtml(medicine.reference_info.uses)}</div>
          <div style="margin-top: 8px"><b>Side effects:</b> ${escapeHtml(medicine.reference_info.side_effects)}</div>
        </div>
      `
      : `
        <div class="info-section info-muted">
          Reference notes are not available for this medicine yet.
        </div>
      `;

    const buyLinks = Array.isArray(medicine.buy_links) ? medicine.buy_links : [];
    const linksHtml = buyLinks.length
      ? `
        <div class="buy-links">
          ${buyLinks.map((link) => `
            <a class="buy-link" href="${escapeHtml(link.url)}" target="_blank" rel="noopener noreferrer">
              ${escapeHtml(link.label)}
            </a>
          `).join('')}
        </div>
      `
      : '';

    list.innerHTML += `
      <div class="medicine-card">
        <div class="medicine-name">${index + 1}. ${escapeHtml(medicine.corrected)}</div>
        <div class="medicine-subtitle">External links search this medicine on online pharmacy websites.</div>
        ${referenceHtml}
        ${linksHtml}
      </div>
    `;
  });

  card.style.display = 'block';
}

async function translateAll(targetLanguage) {
  if (!baseResults) return;

  if (targetLanguage === 'English') {
    currentResults = deepClone(baseResults);
    activeLanguage = 'English';
    renderResults();
    return;
  }

  const items = baseResults.medicines
    .filter((medicine) => medicine.reference_info && medicine.reference_info.found)
    .map((medicine) => ({
      name: medicine.corrected,
      uses: medicine.reference_info.uses,
      side_effects: medicine.reference_info.side_effects,
    }));

  if (!items.length) return;

  languageButtons.forEach((button) => { button.disabled = true; });

  try {
    const response = await fetch('/translate_references', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items,
        target_language: targetLanguage,
      }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Translation failed');
    }

    const translatedMap = new Map(
      (data.items || []).map((item) => [String(item.name || '').toLowerCase(), item])
    );

    currentResults = deepClone(baseResults);
    currentResults.medicines = currentResults.medicines.map((medicine) => {
      const translated = translatedMap.get(String(medicine.corrected || '').toLowerCase());
      if (translated && medicine.reference_info && medicine.reference_info.found) {
        medicine.reference_info = {
          found: true,
          uses: translated.uses,
          side_effects: translated.side_effects,
        };
      }
      return medicine;
    });

    activeLanguage = targetLanguage;
    renderResults();
  } catch (error) {
    alert('Translation error: ' + error.message);
  } finally {
    languageButtons.forEach((button) => { button.disabled = false; });
  }
}

function setPharmacyStatus(message, isError = false) {
  pharmacyStatus.textContent = message || '';
  pharmacyStatus.classList.toggle('status-error', Boolean(isError));
}

function formatDistance(meters) {
  const value = Number(meters || 0);
  if (value >= 1000) {
    return `${(value / 1000).toFixed(2)} km`;
  }
  return `${Math.round(value)} m`;
}

function formatDuration(seconds) {
  const minutes = Math.round(Number(seconds || 0) / 60);
  if (minutes < 60) {
    return `${Math.max(minutes, 1)} min`;
  }
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return `${hours} hr ${remainder} min`;
}

function buildOsmDirectionsUrl(pharmacy) {
  if (!userLocation || !pharmacy) return 'https://www.openstreetmap.org';
  const start = `${userLocation.lat},${userLocation.lon}`;
  const end = `${pharmacy.lat},${pharmacy.lon}`;
  return `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${encodeURIComponent(start)};${encodeURIComponent(end)}`;
}

function getCurrentPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Location is not supported in this browser.'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({
        lat: position.coords.latitude,
        lon: position.coords.longitude,
      }),
      () => reject(new Error('Location permission was denied or unavailable.')),
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 }
    );
  });
}

function initializePharmacyMap() {
  if (!window.L || !userLocation) return false;

  if (!pharmacyMap) {
    pharmacyMap = L.map('pharmacyMap');
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(pharmacyMap);
  }

  pharmacyMap.setView([userLocation.lat, userLocation.lon], 14);
  if (userMarker) {
    userMarker.setLatLng([userLocation.lat, userLocation.lon]);
  } else {
    userMarker = L.marker([userLocation.lat, userLocation.lon]).addTo(pharmacyMap).bindPopup('Your location');
  }
  setTimeout(() => pharmacyMap.invalidateSize(), 50);
  return true;
}

function clearPharmacyMap() {
  if (!pharmacyMap) return;
  pharmacyMarkers.forEach((marker) => marker.remove());
  pharmacyMarkers = [];
  if (routeLine) {
    routeLine.remove();
    routeLine = null;
  }
}

function drawPharmacyMarkers() {
  if (!initializePharmacyMap()) return;
  clearPharmacyMap();

  pharmacies.forEach((pharmacy, index) => {
    const marker = L.marker([pharmacy.lat, pharmacy.lon])
      .addTo(pharmacyMap)
      .bindPopup(`${index + 1}. ${escapeHtml(pharmacy.name)}<br>${formatDistance(pharmacy.distance_m)}`);
    marker.on('click', () => selectRoute(pharmacy.id));
    pharmacyMarkers.push(marker);
  });

  const bounds = L.latLngBounds([[userLocation.lat, userLocation.lon]]);
  pharmacies.forEach((pharmacy) => bounds.extend([pharmacy.lat, pharmacy.lon]));
  pharmacyMap.fitBounds(bounds, { padding: [28, 28], maxZoom: 15 });
}

function renderPharmacyList() {
  if (!pharmacies.length) {
    pharmacyList.innerHTML = '<div class="info-section info-muted">No nearby medical stores found within 2 km.</div>';
    return;
  }

  pharmacyList.innerHTML = pharmacies.map((pharmacy, index) => {
    const address = pharmacy.address ? escapeHtml(pharmacy.address) : 'Address not available';
    return `
      <div class="pharmacy-item">
        <div class="pharmacy-name">${index + 1}. ${escapeHtml(pharmacy.name)}</div>
        <div class="pharmacy-meta">${formatDistance(pharmacy.distance_m)} away<br>${address}</div>
        <div class="results-actions">
          <button class="copy-btn" type="button" onclick="selectRoute('${escapeHtml(pharmacy.id)}')">Select Route</button>
          <a class="buy-link" href="${escapeHtml(buildOsmDirectionsUrl(pharmacy))}" target="_blank" rel="noopener noreferrer">Open Directions</a>
        </div>
      </div>
    `;
  }).join('');
}

async function findNearbyPharmacies() {
  findPharmaciesBtn.disabled = true;
  routeSummary.style.display = 'none';
  mapLayout.style.display = 'none';
  pharmacyList.innerHTML = '';
  setPharmacyStatus('Getting your location...');

  try {
    userLocation = await getCurrentPosition();
    setPharmacyStatus('Searching nearby medical stores...');

    const response = await fetch('/nearby_pharmacies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...userLocation, radius_m: 2000 }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Unable to find nearby medical stores.');
    }

    pharmacies = Array.isArray(data.pharmacies) ? data.pharmacies : [];
    mapLayout.style.display = 'grid';
    renderPharmacyList();

    if (window.L) {
      drawPharmacyMarkers();
      setPharmacyStatus(pharmacies.length ? `Found ${pharmacies.length} medical stores within 2 km.` : 'No medical stores found within 2 km.');
    } else {
      setPharmacyStatus('Map could not load, but nearby medical stores are listed below.', true);
    }
  } catch (error) {
    setPharmacyStatus(error.message, true);
  } finally {
    findPharmaciesBtn.disabled = false;
  }
}

async function selectRoute(pharmacyId) {
  const pharmacy = pharmacies.find((item) => item.id === pharmacyId);
  if (!pharmacy || !userLocation) return;

  routeSummary.style.display = 'block';
  routeSummary.textContent = `Finding shortest route to ${pharmacy.name}...`;

  try {
    const response = await fetch('/route_to_pharmacy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start: userLocation,
        end: { lat: pharmacy.lat, lon: pharmacy.lon },
      }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Unable to find route.');
    }

    routeSummary.innerHTML = `
      Shortest driving route to ${escapeHtml(pharmacy.name)}:
      ${formatDistance(data.distance_m)} - ${formatDuration(data.duration_s)}
      <a class="buy-link" style="margin-left:8px" href="${escapeHtml(buildOsmDirectionsUrl(pharmacy))}" target="_blank" rel="noopener noreferrer">Open Directions</a>
    `;

    if (window.L && pharmacyMap && data.geometry && Array.isArray(data.geometry.coordinates)) {
      if (routeLine) {
        routeLine.remove();
      }
      const latLngs = data.geometry.coordinates.map((point) => [point[1], point[0]]);
      routeLine = L.polyline(latLngs, { color: '#1a73e8', weight: 5 }).addTo(pharmacyMap);
      pharmacyMap.fitBounds(routeLine.getBounds(), { padding: [28, 28] });
    }
  } catch (error) {
    routeSummary.innerHTML = `
      ${escapeHtml(error.message)}
      <a class="buy-link" style="margin-left:8px" href="${escapeHtml(buildOsmDirectionsUrl(pharmacy))}" target="_blank" rel="noopener noreferrer">Open Directions</a>
    `;
  }
}

function buildReadAloudText() {
  const medicines = (currentResults && currentResults.medicines) ? currentResults.medicines : [];
  if (!medicines.length) return '';

  return medicines.map((medicine, index) => {
    const info = medicine.reference_info || {};
    const parts = [`Medicine ${index + 1}. ${medicine.corrected || ''}.`];
    if (info.uses) {
      parts.push(`Uses. ${info.uses}.`);
    }
    if (info.side_effects) {
      parts.push(`Side effects. ${info.side_effects}.`);
    }
    return parts.join(' ');
  }).join(' ');
}

function stopReadAloud() {
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  isSpeaking = false;
  if (readAloudBtn) {
    readAloudBtn.textContent = 'Read Aloud';
  }
}

function toggleReadAloud() {
  if (!('speechSynthesis' in window)) {
    alert('Read aloud is not supported in this browser.');
    return;
  }

  if (isSpeaking) {
    stopReadAloud();
    return;
  }

  const text = buildReadAloudText();
  if (!text) {
    alert('No medicine details are available to read aloud.');
    return;
  }

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = languageVoiceHints[activeLanguage] || 'en-IN';
  utterance.rate = 0.95;
  utterance.onend = stopReadAloud;
  utterance.onerror = stopReadAloud;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
  isSpeaking = true;
  readAloudBtn.textContent = 'Stop Audio';
}

function copyList() {
  const medicines = (currentResults && currentResults.medicines) ? currentResults.medicines : [];
  const text = medicines
    .map((medicine) => medicine.corrected)
    .join('\\n');
  navigator.clipboard.writeText(text);
  alert('Copied to clipboard!');
}
</script>
</body>
</html>'''


if __name__ == "__main__":
    app.run(debug=False, port=5000)
