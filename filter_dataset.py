# filter_dataset.py
# Remove classes with fewer than 3 real samples
# Run from project root

import os, shutil
from collections import Counter
import re

src = 'dataset/train'
files = [f for f in os.listdir(src) if f.endswith(('.png','.jpg'))]

# Count ORIGINAL files only (no aug, no syn)
original = [f for f in files if '_aug' not in f and '_syn' not in f]
labels = [re.split(r'_\d|_[a-z]{3,}', os.path.splitext(f)[0])[0].lower() 
          for f in original]
counts = Counter(labels)

# Keep only classes with ≥3 original samples
keep = {label for label, count in counts.items() if count >= 3}
remove = {label for label, count in counts.items() if count < 3}

print(f"Keeping {len(keep)} classes, removing {len(remove)} classes")
print(f"Removed: {sorted(remove)}")

# Remove all images (including augmented) for dropped classes
# from ALL splits
for split in ['train', 'val', 'test']:
    folder = f'dataset/{split}'
    removed = 0
    for f in os.listdir(folder):
        label = re.split(r'_\d|_[a-z]{3,}', os.path.splitext(f)[0])[0].lower()
        if label in remove:
            os.remove(os.path.join(folder, f))
            removed += 1
    print(f"{split}: removed {removed} files")

print("Done. Recreate LMDB after this.")