import { useEffect, useRef, useState } from 'react';
import ReactCrop, { centerCrop, makeAspectCrop } from 'react-image-crop';
import 'react-image-crop/dist/ReactCrop.css';

function centerFullCrop(width, height) {
  return centerCrop(makeAspectCrop({ unit: '%', width: 88 }, width / height, width, height), width, height);
}

/**
 * @param {{onExtract: (file: File, previewUrl: string) => void}} props
 */
export default function UploadZone({ onExtract }) {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [crop, setCrop] = useState();
  const [completedCrop, setCompletedCrop] = useState();
  const [dragging, setDragging] = useState(false);
  const imageRef = useRef(null);

  function loadFile(nextFile) {
    if (!nextFile || !nextFile.type.startsWith('image/')) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(nextFile);
    setPreviewUrl(URL.createObjectURL(nextFile));
  }

  useEffect(() => {
    const onPaste = (event) => {
      const imageItem = Array.from(event.clipboardData?.items || []).find((item) => item.type.startsWith('image/'));
      if (imageItem) loadFile(imageItem.getAsFile());
    };
    window.addEventListener('paste', onPaste);
    return () => window.removeEventListener('paste', onPaste);
  });

  async function buildCroppedFile() {
    if (!completedCrop || !imageRef.current || !file) return file;
    const image = imageRef.current;
    const canvas = document.createElement('canvas');
    const scaleX = image.naturalWidth / image.width;
    const scaleY = image.naturalHeight / image.height;
    canvas.width = Math.round(completedCrop.width * scaleX);
    canvas.height = Math.round(completedCrop.height * scaleY);
    const context = canvas.getContext('2d');
    context.drawImage(
      image,
      completedCrop.x * scaleX,
      completedCrop.y * scaleY,
      completedCrop.width * scaleX,
      completedCrop.height * scaleY,
      0,
      0,
      canvas.width,
      canvas.height,
    );
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
    return new File([blob], 'cropped-prescription.png', { type: 'image/png' });
  }

  async function handleExtract() {
    if (!file) return;
    const croppedFile = await buildCroppedFile();
    onExtract(croppedFile, previewUrl);
  }

  return (
    <div>
      <label
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          loadFile(event.dataTransfer.files?.[0]);
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-3xl border border-dashed p-8 text-center transition ${
          dragging
            ? 'animate-pulseBorder border-clinic-cyan bg-clinic-cyan/10 shadow-glow'
            : 'border-clinic-cyan/40 bg-white/[0.04] hover:border-clinic-cyan hover:bg-clinic-cyan/5'
        }`}
      >
        <input type="file" accept="image/*" className="hidden" onChange={(event) => loadFile(event.target.files?.[0])} />
        <div className="mb-4 rounded-full border border-clinic-cyan/30 bg-clinic-cyan/10 px-4 py-2 font-mono text-xs uppercase tracking-wide text-clinic-cyan">
          Drag, click, or paste image
        </div>
        <p className="text-lg font-semibold text-clinic-bone">Upload handwritten prescription</p>
        <p className="mt-2 text-sm text-clinic-muted">Or paste image from clipboard while this page is open.</p>
      </label>

      {previewUrl && (
        <div className="mt-6 rounded-3xl border border-white/10 bg-black/20 p-4">
          <ReactCrop crop={crop} onChange={setCrop} onComplete={setCompletedCrop} keepSelection>
            <img
              ref={imageRef}
              src={previewUrl}
              alt="Prescription preview"
              className="max-h-[58vh] w-full rounded-2xl object-contain"
              onLoad={(event) => {
                const { naturalWidth, naturalHeight } = event.currentTarget;
                setCrop(centerFullCrop(naturalWidth, naturalHeight));
              }}
            />
          </ReactCrop>

          <button
            type="button"
            onClick={handleExtract}
            className="mt-5 w-full rounded-2xl bg-[linear-gradient(110deg,#00e5cc,white,#00e5cc)] bg-[length:220%_100%] px-6 py-4 font-mono text-sm font-bold uppercase tracking-[0.22em] text-clinic-void shadow-glow transition hover:scale-[1.01] active:scale-[0.99] animate-shimmer"
          >
            Extract Medicines
          </button>
        </div>
      )}
    </div>
  );
}
