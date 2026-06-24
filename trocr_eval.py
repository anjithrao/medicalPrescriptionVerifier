import os, re, torch, sys
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
sys.path.insert(0, 'crnn-pytorch')
from correct import correct

def edit_distance(s1, s2):
    m, n = len(s1), len(s2)
    dp = list(range(n+1))
    for i in range(1, m+1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, n+1):
            dp[j] = prev[j-1] if s1[i-1]==s2[j-1] else 1+min(prev[j],dp[j-1],prev[j-1])
    return dp[n]

print("Loading model...")
processor = TrOCRProcessor.from_pretrained('./trocr_best')
model = VisionEncoderDecoderModel.from_pretrained('./trocr_best')
model.eval()
if torch.cuda.is_available():
    model = model.cuda()

test_folder = 'dataset/test'
files = [f for f in os.listdir(test_folder) if f.lower().endswith(('.png','.jpg'))]

raw_correct = 0
corr_correct = 0
total = 0
raw_cer_total = 0
corr_cer_total = 0
rows = []

for fname in files:
    gt = re.split(r'_\d|_[a-z]{3,}', os.path.splitext(fname)[0])[0].lower()
    img = Image.open(os.path.join(test_folder, fname)).convert('RGB')
    pv = processor(img, return_tensors='pt').pixel_values
    if torch.cuda.is_available():
        pv = pv.cuda()
    with torch.no_grad():
        out = model.generate(pv, max_new_tokens=32)
    raw = processor.batch_decode(out, skip_special_tokens=True)[0].strip().lower()
    corrected, score, status = correct(raw)

    r_cer = edit_distance(raw, gt) / max(len(gt), 1)
    c_cer = edit_distance(corrected, gt) / max(len(gt), 1)
    raw_cer_total += r_cer
    corr_cer_total += c_cer
    if raw == gt: raw_correct += 1
    if corrected == gt: corr_correct += 1
    total += 1
    rows.append((gt, raw, corrected, round(r_cer,3), round(c_cer,3)))

print(f"\n{'='*60}")
print(f"TrOCR RESULTS ON TEST SET ({total} samples)")
print(f"{'='*60}")
print(f"                   RAW        AFTER CORRECTION")
print(f"Word Accuracy:    {raw_correct/total*100:5.1f}%      {corr_correct/total*100:5.1f}%")
print(f"Mean CER:         {raw_cer_total/total*100:5.1f}%      {corr_cer_total/total*100:5.1f}%")
print(f"{'='*60}")
print(f"\n{'GT':<22} {'RAW':<22} {'CORRECTED':<22} R_CER  C_CER")
print('-'*75)
for gt, raw, corr, r, c in rows:
    m = '✓' if corr==gt else '✗'
    print(f"{m} {gt:<21} {raw:<22} {corr:<22} {r:<7} {c}")

with open('trocr_results.txt','w') as f:
    f.write(f"Word Accuracy Raw: {raw_correct/total*100:.1f}%\n")
    f.write(f"Word Accuracy Corrected: {corr_correct/total*100:.1f}%\n")
    f.write(f"CER Raw: {raw_cer_total/total*100:.1f}%\n")
    f.write(f"CER Corrected: {corr_cer_total/total*100:.1f}%\n\n")
    for gt, raw, corr, r, c in rows:
        f.write(f"GT: {gt:<22} RAW: {raw:<22} CORR: {corr}\n")
print("\nSaved to trocr_results.txt")