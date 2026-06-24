import { useMemo, useState } from 'react';

const extensions = ['jpg', 'jpeg', 'png', 'webp'];

function initialsFor(name) {
  return String(name || 'RX')
    .split(/[-\s]+/)
    .map((part) => part[0])
    .join('')
    .slice(0, 3)
    .toUpperCase();
}

/**
 * @param {{medicineName: string}} props
 */
export default function MedicineImage({ medicineName }) {
  const safeName = String(medicineName || '').toLowerCase();
  const [extensionIndex, setExtensionIndex] = useState(0);
  const imgSrc = useMemo(() => {
    if (extensionIndex >= extensions.length) return null;
    return `/static/medicine_images/${safeName}.${extensions[extensionIndex]}`;
  }, [extensionIndex, safeName]);

  if (!imgSrc) {
    return (
      <div className="flex h-44 flex-col items-center justify-center rounded-t-xl border-b border-clinic-cyan/15 bg-white/[0.03]">
        <svg viewBox="0 0 120 120" className="h-20 w-20 text-clinic-cyan opacity-40" aria-hidden="true">
          <rect x="23" y="48" width="74" height="24" rx="12" fill="currentColor" />
          <path d="M60 49v22" stroke="#0a0e17" strokeWidth="5" strokeLinecap="round" />
          <circle cx="42" cy="60" r="4" fill="#0a0e17" />
          <circle cx="78" cy="60" r="4" fill="#0a0e17" />
        </svg>
        <div className="mt-2 font-mono text-sm tracking-[0.25em] text-clinic-muted">{initialsFor(medicineName)}</div>
      </div>
    );
  }

  return (
    <div className="group relative h-44 overflow-hidden rounded-t-xl border-b border-clinic-cyan/15 bg-white/[0.03]">
      <img
        src={imgSrc}
        alt={`${medicineName} packet`}
        className="h-full w-full object-contain p-3 transition-transform duration-300 group-hover:scale-[1.04]"
        onError={() => setExtensionIndex((index) => index + 1)}
      />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-clinic-panel via-clinic-panel/50 to-transparent" />
    </div>
  );
}
