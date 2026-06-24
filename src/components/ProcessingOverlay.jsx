/**
 * @param {{isVisible: boolean, previewUrl?: string}} props
 */
export default function ProcessingOverlay({isVisible, previewUrl}) {
  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-clinic-void/90 p-4 backdrop-blur-xl">
      <div className="w-full max-w-3xl rounded-3xl border border-clinic-cyan/30 bg-white/[0.08] p-6 shadow-card">
        <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-black/40">
          {previewUrl ? (
            <img
              src={previewUrl}
              alt="Prescription scan preview"
              className="h-72 w-full object-contain opacity-70"
            />
          ) : (
            <div className="h-72" />
          )}
          <div className="absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-clinic-cyan/50 to-transparent blur-sm animate-scan" />
          <div className="absolute inset-0 bg-[linear-gradient(transparent_95%,rgba(0,229,204,0.24)_96%)] bg-[length:100%_18px]" />
        </div>
        <div className="mt-6 flex flex-wrap justify-center gap-3 font-mono text-xs uppercase tracking-wide text-clinic-cyan">
          <span>Running EasyOCR</span>
          <span>TrOCR refinement</span>
          <span>Preparing notes</span>
        </div>
      </div>
    </div>
  );
}
