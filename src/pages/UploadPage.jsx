import HeroScene from '../components/HeroScene.jsx';
import UploadZone from '../components/UploadZone.jsx';

/**
 * @param {{onExtract: (file: File, previewUrl: string) => void, error?: string}} props
 */
export default function UploadPage({ onExtract, error }) {
  return (
    <main className="relative min-h-screen">
      <HeroScene />
      <section className="relative z-10 flex min-h-screen items-center justify-center px-4 py-16">
        <div className="w-full max-w-3xl rounded-3xl border border-white/15 bg-white/[0.07] p-6 shadow-card backdrop-blur-2xl md:p-10">
          <div className="mb-8 text-center">
            <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-clinic-cyan/50 bg-clinic-cyan/10 shadow-glow">
              <span className="font-mono text-2xl font-bold text-clinic-cyan">Rx</span>
            </div>
            <p className="font-mono text-xs uppercase tracking-[0.42em] text-clinic-cyan">Clinical OCR System</p>
            <h1 className="mt-4 font-mono text-4xl font-bold tracking-tight text-clinic-bone md:text-6xl">RxReader</h1>
            <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-clinic-muted md:text-lg">
              Decode handwritten prescriptions, verify medicines, translate patient guidance, and locate nearby care points.
            </p>
          </div>

          {error && (
            <div className="mb-5 rounded-2xl border border-clinic-red/40 bg-clinic-red/10 p-4 text-sm text-rose-100">
              {error}
            </div>
          )}

          <UploadZone onExtract={onExtract} />
        </div>
      </section>
    </main>
  );
}
