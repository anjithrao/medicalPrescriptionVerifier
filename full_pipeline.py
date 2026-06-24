import sys, os, torch
import easyocr
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
sys.path.insert(0, 'crnn-pytorch')
from correct import correct

MEDICINE_PREFIXES = ['tab','tab.','cap','cap.','inj','inj.',
                     'syr','syr.','t.','tb.','c.','oint','drops']

def is_prefix(text):
    return text.lower().strip().rstrip('.') in [
        p.rstrip('.') for p in MEDICINE_PREFIXES]

def is_dosage(text):
    import re
    patterns = [r'\d+\s*mg',r'\d+\s*ml',r'\d+-\d+-\d+',
                r'\b(od|bd|tds|qid|sos|ac|pc|hs)\b',r'^\d+$']
    return any(re.search(p, text.lower()) for p in patterns)

print("Loading EasyOCR...")
reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())

print("Loading TrOCR...")
processor = TrOCRProcessor.from_pretrained('./trocr_best')
model = VisionEncoderDecoderModel.from_pretrained('./trocr_best')
model.eval()
if torch.cuda.is_available():
    model = model.cuda()

def recognize(crop_pil):
    pv = processor(crop_pil.convert('RGB'), return_tensors='pt').pixel_values
    if torch.cuda.is_available():
        pv = pv.cuda()
    with torch.no_grad():
        out = model.generate(pv, max_new_tokens=32)
    return processor.batch_decode(out, skip_special_tokens=True)[0].strip().lower()

def process(image_path):
    print(f"\nProcessing: {image_path}")
    img = Image.open(image_path)
    results = reader.readtext(image_path)
    print(f"EasyOCR found {len(results)} regions")

    sorted_results = sorted(results,
        key=lambda x: (min(p[1] for p in x[0]), min(p[0] for p in x[0])))

    medicine_regions = []
    for i, (bbox, text, conf) in enumerate(sorted_results):
        if not is_prefix(text):
            continue
        y1c = min(p[1] for p in bbox)
        y2c = max(p[1] for p in bbox)
        x1c = min(p[0] for p in bbox)
        for bbox2, text2, conf2 in sorted_results[i+1:]:
            x1n = min(p[0] for p in bbox2)
            y1n = min(p[1] for p in bbox2)
            y2n = max(p[1] for p in bbox2)
            overlap = min(y2c,y2n) - max(y1c,y1n)
            height = max(y2c-y1c, y2n-y1n)
            if overlap > height*0.3 and x1n > x1c:
                if not is_dosage(text2):
                    x1 = max(0, int(min(p[0] for p in bbox2))-4)
                    y1 = max(0, int(min(p[1] for p in bbox2))-4)
                    x2 = min(img.width,  int(max(p[0] for p in bbox2))+4)
                    y2 = min(img.height, int(max(p[1] for p in bbox2))+4)
                    medicine_regions.append({
                        'bbox':(x1,y1,x2,y2),
                        'easy_text':text2,
                        'prefix':text
                    })
                break

    # Fallback if no prefixes found
    if not medicine_regions:
        print("No Tab./Cap./Inj. found — using fallback (all text regions)")
        for bbox, text, conf in sorted_results:
            if len(text) > 3 and not is_dosage(text) and not is_prefix(text):
                x1=max(0,int(min(p[0] for p in bbox))-4)
                y1=max(0,int(min(p[1] for p in bbox))-4)
                x2=min(img.width, int(max(p[0] for p in bbox))+4)
                y2=min(img.height,int(max(p[1] for p in bbox))+4)
                medicine_regions.append({'bbox':(x1,y1,x2,y2),
                                        'easy_text':text,'prefix':'?'})

    print(f"Medicine regions found: {len(medicine_regions)}")
    print(f"\n{'#':<4} {'PREFIX':<8} {'EASYOCR':<18} {'TROCR':<18} {'CORRECTED':<18} CONF")
    print('-'*75)

    medicines = []
    seen = set()
    for i, region in enumerate(medicine_regions, 1):
        crop = img.crop(region['bbox'])
        raw = recognize(crop)
        corrected, score, status = correct(raw)
        if corrected in seen:
            continue
        seen.add(corrected)
        flag = '' if status=='corrected' else '⚠' if status=='uncertain' else '?'
        print(f"{i:<4} {region['prefix']:<8} {region['easy_text']:<18} "
              f"{raw:<18} {corrected:<18} {score:.0f}% {flag}")
        medicines.append(corrected)

    print(f"\n{'='*50}")
    print("MEDICINES EXTRACTED:")
    for i, m in enumerate(medicines, 1):
        print(f"  {i}. {m}")
    print(f"{'='*50}")
    return medicines

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv)>1 else input("Prescription image path: ")
    process(path)