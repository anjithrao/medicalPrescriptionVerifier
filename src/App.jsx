import { useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import UploadPage from './pages/UploadPage.jsx';
import ResultsPage from './pages/ResultsPage.jsx';
import PharmaciesPage from './pages/PharmaciesPage.jsx';
import ProcessingOverlay from './components/ProcessingOverlay.jsx';
import { processPrescription, translateReferences } from './api.js';

const pageVariants = {
  initial: { opacity: 0, x: 44 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -44 },
};

export const LANGUAGES = [
  'English',
  'Assamese',
  'Bengali',
  'Bodo',
  'Dogri',
  'Gujarati',
  'Hindi',
  'Kannada',
  'Kashmiri',
  'Konkani',
  'Maithili',
  'Malayalam',
  'Manipuri',
  'Marathi',
  'Nepali',
  'Odia',
  'Punjabi',
  'Sanskrit',
  'Santali',
  'Sindhi',
  'Tamil',
  'Telugu',
  'Urdu',
];

export default function App() {
  const [step, setStep] = useState('upload');
  const [baseResults, setBaseResults] = useState(null);
  const [currentResults, setCurrentResults] = useState(null);
  const [activeLanguage, setActiveLanguage] = useState('English');
  const [isProcessing, setIsProcessing] = useState(false);
  const [previewUrl, setPreviewUrl] = useState('');
  const [error, setError] = useState('');

  const medicines = currentResults?.medicines || [];
  const hasResults = medicines.length > 0;

  const navigation = useMemo(
    () => [
      { id: 'upload', label: 'Upload', enabled: true },
      { id: 'results', label: 'Results', enabled: Boolean(currentResults) },
      { id: 'pharmacies', label: 'Pharmacies', enabled: Boolean(currentResults) },
    ],
    [currentResults],
  );

  async function handleExtract(croppedFile, imagePreviewUrl) {
    setError('');
    setPreviewUrl(imagePreviewUrl);
    setIsProcessing(true);
    try {
      const data = await processPrescription(croppedFile);
      setBaseResults(data);
      setCurrentResults(data);
      setActiveLanguage('English');
      setStep('results');
    } catch (extractError) {
      setError(extractError.message);
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleTranslate(language) {
    if (!baseResults) return;
    setError('');

    if (language === 'English') {
      setCurrentResults(baseResults);
      setActiveLanguage('English');
      return;
    }

    const items = (baseResults.medicines || [])
      .filter((medicine) => medicine.reference_info?.found)
      .map((medicine) => ({
        name: medicine.corrected,
        uses: medicine.reference_info.uses,
        side_effects: medicine.reference_info.side_effects,
      }));

    try {
      const data = await translateReferences(items, language);
      const translatedMap = new Map((data.items || []).map((item) => [String(item.name || '').toLowerCase(), item]));
      const translatedResults = {
        ...baseResults,
        medicines: (baseResults.medicines || []).map((medicine) => {
          const translated = translatedMap.get(String(medicine.corrected || '').toLowerCase());
          if (!translated || !medicine.reference_info?.found) return medicine;
          return {
            ...medicine,
            reference_info: {
              found: true,
              uses: translated.uses,
              side_effects: translated.side_effects,
            },
          };
        }),
      };
      setCurrentResults(translatedResults);
      setActiveLanguage(language);
    } catch (translateError) {
      setError(translateError.message);
    }
  }

  return (
    <div className="min-h-screen overflow-x-hidden bg-clinic-void text-clinic-bone">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_top_left,rgba(0,229,204,0.14),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(20,184,166,0.12),transparent_34%)]" />

      {hasResults && (
        <nav className="fixed left-1/2 top-4 z-40 flex -translate-x-1/2 gap-2 rounded-full border border-white/10 bg-clinic-panel/70 p-2 shadow-card backdrop-blur-xl">
          {navigation.map((item) => (
            <button
              key={item.id}
              type="button"
              disabled={!item.enabled}
              onClick={() => setStep(item.id)}
              className={`rounded-full px-4 py-2 font-mono text-xs uppercase tracking-wide transition ${
                step === item.id
                  ? 'bg-clinic-cyan text-clinic-void shadow-glow'
                  : 'text-clinic-muted hover:bg-white/10 hover:text-clinic-bone disabled:cursor-not-allowed disabled:opacity-40'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      )}

      <AnimatePresence mode="wait">
        {step === 'upload' && (
          <motion.div key="upload" variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <UploadPage onExtract={handleExtract} error={error} />
          </motion.div>
        )}

        {step === 'results' && currentResults && (
          <motion.div key="results" variants={pageVariants} initial="initial" animate="animate" exit="exit">
            <ResultsPage
              results={currentResults}
              activeLanguage={activeLanguage}
              languages={LANGUAGES}
              onTranslate={handleTranslate}
              onOpenPharmacies={() => setStep('pharmacies')}
              error={error}
            />
          </motion.div>
        )}

        {step === 'pharmacies' && currentResults && (
          <motion.div key="pharmacies" variants={pageVariants} initial={{ opacity: 0, x: 120 }} animate="animate" exit="exit">
            <PharmaciesPage onBack={() => setStep('results')} />
          </motion.div>
        )}
      </AnimatePresence>

      <ProcessingOverlay isVisible={isProcessing} previewUrl={previewUrl} />
    </div>
  );
}
