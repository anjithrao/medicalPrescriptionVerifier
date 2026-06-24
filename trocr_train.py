import os, re, torch
from pathlib import Path
from PIL import Image
from torch.utils.data import Dataset
from transformers import (
    TrOCRProcessor,
    VisionEncoderDecoderModel,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    default_data_collator
)

print("Transformers version:", __import__('transformers').__version__)

class MedicineDataset(Dataset):
    def __init__(self, folder, processor, max_target_length=32):
        self.processor = processor
        self.max_target_length = max_target_length
        self.samples = []
        for fname in os.listdir(folder):
            if not fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
            base = os.path.splitext(fname)[0]
            label = re.split(r'_\d|_[a-z]{3,}', base)[0].lower()
            if re.search(r'[^a-z\-1]', label):
                continue
            self.samples.append((os.path.join(folder, fname), label))
        print(f"Loaded {len(self.samples)} samples from {folder}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert('RGB')
        pixel_values = self.processor(image, return_tensors='pt').pixel_values
        labels = self.processor.tokenizer(
            label,
            padding='max_length',
            max_length=self.max_target_length,
            return_tensors='pt'
        ).input_ids
        labels[labels == self.processor.tokenizer.pad_token_id] = -100
        return {'pixel_values': pixel_values.squeeze(), 'labels': labels.squeeze()}


def compute_metrics(pred):
    labels_ids = pred.label_ids
    pred_ids   = pred.predictions
    labels_ids[labels_ids == -100] = processor.tokenizer.pad_token_id
    pred_str  = processor.batch_decode(pred_ids, skip_special_tokens=True)
    label_str = processor.batch_decode(labels_ids, skip_special_tokens=True)
    correct = sum(p.strip() == g.strip() for p, g in zip(pred_str, label_str))
    acc = correct / len(label_str)
    print("\nSample predictions:")
    for p, g in zip(pred_str[:5], label_str[:5]):
        mark = '✓' if p.strip()==g.strip() else '✗'
        print(f"  {mark} pred: {p:<20} gt: {g}")
    return {'word_accuracy': acc}


if __name__ == "__main__":
    processor = TrOCRProcessor.from_pretrained('microsoft/trocr-base-handwritten', backend="torchvision")
    model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-handwritten')
    model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.vocab_size = model.config.decoder.vocab_size

    train_dataset = MedicineDataset('dataset/train', processor)
    val_dataset   = MedicineDataset('dataset/val', processor)
    test_dataset  = MedicineDataset('dataset/test', processor)

    args = Seq2SeqTrainingArguments(
        output_dir='./trocr_output',
        num_train_epochs=3,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        predict_with_generate=True,
        eval_strategy='epoch',
        save_strategy='epoch',
        load_best_model_at_end=True,
        metric_for_best_model='eval_loss',
        logging_steps=50,
        learning_rate=5e-5,
        warmup_steps=100,
        fp16=torch.cuda.is_available(),
        gradient_accumulation_steps=1,
        dataloader_num_workers=2,
        report_to='none'
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        data_collator=default_data_collator,
    )

    print("Starting training...")
    trainer.train()
    trainer.save_model('./trocr_best')
    processor.save_pretrained('./trocr_best')
    print("Done. Best model saved to ./trocr_best")