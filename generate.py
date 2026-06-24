import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Graph 1: Accuracy Comparison Bar Chart ────────────────────
fig, ax = plt.subplots(figsize=(12, 7))
models = ['CRNN\n(Baseline)', 'CRNN +\nCorrection', 'TrOCR\nEpoch 1', 'TrOCR\nEpoch 2', 'TrOCR +\nCorrection']
accs   = [13.7, 35.3, 82.3, 92.4, 98.7]
colors = ['#e53935','#fb8c00','#64b5f6','#1e88e5','#1a237e']

bars = ax.bar(models, accs, color=colors, width=0.5, zorder=3)
ax.axhline(y=13.7, color='red', linestyle='--', alpha=0.5, label='CRNN Baseline (13.7%)')
ax.set_ylim(0, 110)
ax.set_ylabel('Word Accuracy (%)', fontsize=13)
ax.set_title('Recognition Performance Comparison\nWord Accuracy on Held-out Handwritten Medicine Test Set (79 samples)',
             fontsize=14, fontweight='bold', pad=15)
ax.grid(axis='y', alpha=0.3, zorder=0)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

for bar, val in zip(bars, accs):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
            f'{val}%', ha='center', va='bottom', fontweight='bold', fontsize=12)

ax.annotate('6.7× improvement\nover baseline',
            xy=(3, 92.4), xytext=(3.4, 75),
            arrowprops=dict(arrowstyle='->', color='black'),
            fontsize=10, color='#1a237e', fontweight='bold')

ax.legend(fontsize=10)
ax.set_caption = ax.set_xlabel('')
fig.text(0.5, -0.02,
         'Figure 1: Word accuracy comparison across handwritten prescription recognition configurations',
         ha='center', fontsize=10, style='italic')

plt.tight_layout()
plt.savefig('graph_accuracy_comparison.png', dpi=150, bbox_inches='tight')
print("Saved: graph_accuracy_comparison.png")
plt.close()

# ── Graph 2: Training Loss Curve (CRNN) ──────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
epochs = [0,5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,87,90,95,99]
# approximate from your training log
train_loss = [4.5,2.1,1.2,0.8,0.5,0.35,0.2,0.15,0.12,0.3,0.1,0.09,0.12,0.11,0.08,0.07,0.005,0.001,0.0005,0.0003,0.0002,0.00002]
val_acc    = [0,5,10,5,6,8,12,11,11,1,12,12,8,7,10,13.9,12,12,11,12,11,11]

ax2 = ax.twinx()
l1, = ax.plot(epochs, train_loss, 'b-o', markersize=3, label='Train Loss', linewidth=2)
l2, = ax2.plot(epochs, val_acc, 'r-s', markersize=3, label='Val Accuracy (%)', linewidth=2)

ax.axvline(x=75, color='green', linestyle='--', alpha=0.7, label='Best Epoch (75)')
ax.set_xlabel('Epoch', fontsize=12)
ax.set_ylabel('Training Loss', fontsize=12, color='blue')
ax2.set_ylabel('Validation Word Accuracy (%)', fontsize=12, color='red')
ax.set_title('CRNN Training Dynamics\nTrain Loss vs Validation Accuracy over 100 Epochs',
             fontsize=13, fontweight='bold')
ax.grid(alpha=0.3)

lines = [l1, l2, mpatches.Patch(color='green', label='Best Epoch (75) — 13.9%')]
ax.legend(handles=lines, loc='upper right', fontsize=10)
ax.spines['top'].set_visible(False)
fig.text(0.5, -0.02,
         'Figure 2: CRNN training curve showing overfitting after epoch 87 (train loss → 0, val accuracy plateaus)',
         ha='center', fontsize=10, style='italic')
plt.tight_layout()
plt.savefig('graph_crnn_training.png', dpi=150, bbox_inches='tight')
print("Saved: graph_crnn_training.png")
plt.close()

# ── Graph 3: TrOCR Training Progress ─────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
trocr_epochs = [1, 2, 3]
trocr_val_acc = [82.28, 92.41, 92.41]
trocr_val_loss = [0.2742, 0.1077, 0.1099]

ax2 = ax.twinx()
l1, = ax.plot(trocr_epochs, trocr_val_loss, 'b-o', markersize=8,
              label='Val Loss', linewidth=2.5)
l2, = ax2.plot(trocr_epochs, trocr_val_acc, 'g-s', markersize=8,
               label='Val Word Accuracy (%)', linewidth=2.5)

for i, (e, a) in enumerate(zip(trocr_epochs, trocr_val_acc)):
    ax2.annotate(f'{a}%', (e, a), textcoords='offset points',
                xytext=(5,5), fontweight='bold', color='green', fontsize=11)

ax.set_xlabel('Epoch', fontsize=12)
ax.set_xticks([1,2,3])
ax.set_ylabel('Validation Loss', fontsize=12, color='blue')
ax2.set_ylabel('Validation Word Accuracy (%)', fontsize=12, color='green')
ax2.set_ylim(0, 105)
ax.set_title('TrOCR Fine-tuning Progress\n(microsoft/trocr-base-handwritten → Medicine Domain)',
             fontsize=13, fontweight='bold')
ax.grid(alpha=0.3)
ax.legend(loc='upper left', fontsize=10)
ax2.legend(loc='lower right', fontsize=10)
ax.spines['top'].set_visible(False)
fig.text(0.5, -0.02,
         'Figure 3: TrOCR achieves 92.41% validation accuracy within 2 epochs via transfer learning',
         ha='center', fontsize=10, style='italic')
plt.tight_layout()
plt.savefig('graph_trocr_training.png', dpi=150, bbox_inches='tight')
print("Saved: graph_trocr_training.png")
plt.close()

# ── Graph 4: Dataset Distribution ────────────────────────────
fig, ax = plt.subplots(figsize=(14, 5))
medicines_sample = [
    'ecosprin','dolostat','zincovit','amlodipine','clopilet',
    'losartan','sartel','pan','stamlo','axcer','aztar','biozil',
    'belladonna','carticare','linaglip','melonin','novastat',
    'pantop','ranozex','restil'
]
counts = [13,11,11,9,9,9,9,8,7,7,7,7,7,7,7,7,7,7,7,7]
colors_bar = ['#1a73e8' if c>=7 else '#64b5f6' for c in counts]

bars = ax.bar(medicines_sample, counts, color=colors_bar)
ax.axhline(y=4.6, color='red', linestyle='--', alpha=0.7, label='Mean (4.6 samples/class)')
ax.set_xlabel('Medicine Name', fontsize=11)
ax.set_ylabel('Number of Samples', fontsize=11)
ax.set_title('Dataset Class Distribution (Top 20 Medicines)\nShowing Real Sample Counts Before Augmentation',
             fontsize=13, fontweight='bold')
ax.tick_params(axis='x', rotation=45)
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
fig.text(0.5, -0.08,
         'Figure 4: Class distribution showing data imbalance (min:3, max:13, mean:4.6 samples per class)',
         ha='center', fontsize=10, style='italic')
plt.tight_layout()
plt.savefig('graph_dataset_distribution.png', dpi=150, bbox_inches='tight')
print("Saved: graph_dataset_distribution.png")
plt.close()

# ── Graph 5: CER Comparison ───────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
systems = ['CRNN\nRaw', 'CRNN +\nCorrection', 'TrOCR\nRaw', 'TrOCR +\nCorrection']
cer_vals = [56.0, 56.3, 1.3, 1.8]
colors_cer = ['#e53935','#fb8c00','#43a047','#1a73e8']
bars = ax.bar(systems, cer_vals, color=colors_cer, width=0.4)
ax.set_ylabel('Character Error Rate (%)', fontsize=12)
ax.set_title('Character Error Rate (CER) Comparison\nLower is Better', fontsize=13, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
for bar, val in zip(bars, cer_vals):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
            f'{val}%', ha='center', fontweight='bold', fontsize=12)
fig.text(0.5, -0.02,
         'Figure 5: CER comparison — TrOCR reduces character error rate from 56% to 1.3%',
         ha='center', fontsize=10, style='italic')
plt.tight_layout()
plt.savefig('graph_cer_comparison.png', dpi=150, bbox_inches='tight')
print("Saved: graph_cer_comparison.png")
plt.close()

print("\nAll 5 graphs generated successfully.")
print("Files: graph_accuracy_comparison.png, graph_crnn_training.png,")
print("       graph_trocr_training.png, graph_dataset_distribution.png,")
print("       graph_cer_comparison.png")