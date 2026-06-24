import { useState } from 'react';

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

/**
 * @param {{medicines: object[], activeLanguage: string}} props
 */
export default function ReadAloudFAB({ medicines, activeLanguage }) {
  const [speaking, setSpeaking] = useState(false);

  function buildText() {
    return medicines
      .map((medicine, index) => {
        const info = medicine.reference_info || {};
        return [`Medicine ${index + 1}. ${medicine.corrected}.`, info.uses ? `Uses. ${info.uses}.` : '', info.side_effects ? `Side effects. ${info.side_effects}.` : '']
          .filter(Boolean)
          .join(' ');
      })
      .join(' ');
  }

  function stop() {
    window.speechSynthesis?.cancel();
    setSpeaking(false);
  }

  function toggle() {
    if (!('speechSynthesis' in window)) {
      alert('Read aloud is not supported in this browser.');
      return;
    }
    if (speaking) {
      stop();
      return;
    }
    const text = buildText();
    if (!text) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = voiceHints[activeLanguage] || 'hi-IN';
    utterance.rate = 0.95;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    setSpeaking(true);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      className="fixed bottom-6 right-6 z-40 flex items-center gap-3 rounded-full border border-clinic-cyan/50 bg-clinic-cyan px-5 py-4 font-mono text-xs font-bold uppercase text-clinic-void shadow-glow transition hover:scale-105"
    >
      {speaking && (
        <span className="flex h-5 items-center gap-1">
          {[0, 1, 2].map((bar) => (
            <span key={bar} className="h-4 w-1 rounded-full bg-clinic-void animate-waveform" />
          ))}
        </span>
      )}
      {speaking ? 'Stop Audio' : 'Read Aloud'}
    </button>
  );
}
