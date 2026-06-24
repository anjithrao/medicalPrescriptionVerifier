import { AnimatePresence, motion } from 'framer-motion';
import MedicineCard from '../components/MedicineCard.jsx';
import TranslateBar from '../components/TranslateBar.jsx';
import ReadAloudFAB from '../components/ReadAloudFAB.jsx';

/**
 * @param {{results: object, activeLanguage: string, languages: string[], onTranslate: (language: string) => void, onOpenPharmacies: () => void, error?: string}} props
 */
export default function ResultsPage({ results, activeLanguage, languages, onTranslate, onOpenPharmacies, error }) {
  const medicines = results.medicines || [];

  return (
    <main className="relative z-10 min-h-screen px-4 pb-24 pt-24 md:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="sticky top-20 z-30 mb-8 rounded-3xl border border-white/10 bg-clinic-panel/80 p-4 shadow-card backdrop-blur-2xl">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-clinic-cyan">Verification Results</p>
              <h2 className="mt-1 font-mono text-2xl font-bold text-clinic-bone">
                {results.total} medicines - {results.engine}
              </h2>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <TranslateBar languages={languages} activeLanguage={activeLanguage} onChange={onTranslate} />
              <button
                type="button"
                onClick={onOpenPharmacies}
                className="rounded-full border border-clinic-cyan/40 bg-clinic-cyan/10 px-5 py-3 font-mono text-xs uppercase tracking-wide text-clinic-cyan transition hover:bg-clinic-cyan hover:text-clinic-void hover:shadow-glow"
              >
                Nearby Pharmacies
              </button>
            </div>
          </div>
        </header>

        {error && (
          <motion.div
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            className="mb-6 rounded-2xl border border-clinic-red/40 bg-clinic-red/10 p-4 text-sm text-rose-100"
          >
            {error}
          </motion.div>
        )}

        <AnimatePresence mode="wait">
          <motion.div
            key={activeLanguage}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            className="grid gap-5 md:grid-cols-2 xl:grid-cols-3"
          >
            {medicines.map((medicine, index) => (
              <MedicineCard key={`${medicine.corrected}-${index}`} medicine={medicine} index={index} activeLanguage={activeLanguage} />
            ))}
          </motion.div>
        </AnimatePresence>
      </div>

      <ReadAloudFAB medicines={medicines} activeLanguage={activeLanguage} />
    </main>
  );
}
