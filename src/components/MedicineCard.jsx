import { useState } from 'react';
import { motion } from 'framer-motion';
import ConfidenceArc from './ConfidenceArc.jsx';
import MedicineImage from './MedicineImage.jsx';

const voiceHints = {
  English: 'en-IN',
  Hindi: 'hi-IN',
  Tamil: 'ta-IN',
  Telugu: 'te-IN',
  Bengali: 'bn-IN',
  Gujarati: 'gu-IN',
  Kannada: 'kn-IN',
  Malayalam: 'ml-IN',
  Marathi: 'mr-IN',
  Odia: 'or-IN',
  Punjabi: 'pa-IN',
  Urdu: 'ur-IN',
  Nepali: 'ne-NP',
};

function confidenceClass(value) {
  if (typeof value !== 'number') return 'border-t-clinic-cyan';
  if (value >= 90) return 'border-t-clinic-green';
  if (value >= 70) return 'border-t-clinic-amber';
  return 'border-t-clinic-red';
}

/**
 * @param {{medicine: object, index: number, activeLanguage: string}} props
 */
export default function MedicineCard({ medicine, index, activeLanguage }) {
  const [expanded, setExpanded] = useState(false);
  const info = medicine.reference_info || {};
  const buyLink = Array.isArray(medicine.buy_links) ? medicine.buy_links[0] : null;

  function readThisMedicine() {
    if (!('speechSynthesis' in window)) {
      alert('Read aloud is not supported in this browser.');
      return;
    }

    const parts = [
      `Medicine. ${medicine.corrected}.`,
      info.uses ? `Uses. ${info.uses}.` : '',
      info.side_effects ? `Side effects. ${info.side_effects}.` : '',
    ].filter(Boolean);

    const utterance = new SpeechSynthesisUtterance(parts.join(' '));
    utterance.lang = voiceHints[activeLanguage] || 'hi-IN';
    utterance.rate = 0.95;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }

  return (
    <motion.article
      initial={{ opacity: 0, y: 28 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.38 }}
      className={`overflow-hidden rounded-xl border border-white/10 border-t-4 bg-white/[0.065] shadow-card backdrop-blur-xl transition hover:border-clinic-cyan/40 hover:shadow-glow ${confidenceClass(medicine.confidence)}`}
    >
      <MedicineImage medicineName={medicine.corrected} />

      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap gap-2">
              {medicine.prefix && (
                <span className="rounded-full border border-clinic-cyan/30 bg-clinic-cyan/10 px-3 py-1 font-mono text-[10px] uppercase text-clinic-cyan">
                  {medicine.prefix}
                </span>
              )}
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-[10px] uppercase text-clinic-muted">
                {medicine.status || 'verified'}
              </span>
            </div>
            <h3 className="mt-3 font-mono text-2xl font-bold text-clinic-bone">{medicine.corrected}</h3>
            {medicine.raw_ocr && <p className="mt-1 text-xs text-clinic-muted">OCR: {medicine.raw_ocr}</p>}
          </div>
          <ConfidenceArc value={medicine.confidence} />
        </div>

        <div className="mt-5 space-y-4 text-sm leading-6 text-clinic-muted">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-clinic-cyan">Uses</p>
            <p className={`${expanded ? '' : 'line-clamp-3'}`}>{info.uses || 'Reference notes are not available for this medicine yet.'}</p>
          </div>
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-clinic-cyan">Side Effects</p>
            <p className={`${expanded ? '' : 'line-clamp-3'}`}>{info.side_effects || 'No side-effect summary available.'}</p>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={readThisMedicine}
            aria-label={`Read ${medicine.corrected} aloud`}
            title="Read this medicine"
            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-clinic-cyan/40 bg-clinic-cyan/10 text-clinic-cyan transition hover:bg-clinic-cyan hover:text-clinic-void hover:shadow-glow"
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" aria-hidden="true">
              <path d="M4 10v4h4l5 4V6l-5 4H4Z" fill="currentColor" />
              <path d="M16 9c.8.8 1.2 1.8 1.2 3s-.4 2.2-1.2 3M18.5 6.5A7.6 7.6 0 0 1 21 12a7.6 7.6 0 0 1-2.5 5.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            className="rounded-full border border-white/15 px-4 py-2 font-mono text-xs uppercase text-clinic-muted transition hover:border-clinic-cyan hover:text-clinic-cyan"
          >
            {expanded ? 'Collapse' : 'Full Info'}
          </button>
          {buyLink && (
            <a
              href={buyLink.url}
              target="_blank"
              rel="noreferrer"
              className="rounded-full bg-clinic-cyan px-4 py-2 font-mono text-xs uppercase text-clinic-void transition hover:shadow-glow"
            >
              Buy Online
            </a>
          )}
        </div>
      </div>
    </motion.article>
  );
}
