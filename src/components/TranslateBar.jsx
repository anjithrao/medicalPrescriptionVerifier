/**
 * @param {{languages: string[], activeLanguage: string, onChange: (language: string) => void}} props
 */
export default function TranslateBar({ languages, activeLanguage, onChange }) {
  return (
    <label className="flex items-center gap-3 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2">
      <span className="font-mono text-xs uppercase tracking-wide text-clinic-muted">Translate</span>
      <select
        value={activeLanguage}
        onChange={(event) => onChange(event.target.value)}
        className="bg-transparent font-mono text-sm text-clinic-bone outline-none"
      >
        {languages.map((language) => (
          <option key={language} value={language} className="bg-clinic-panel text-clinic-bone">
            {language}
          </option>
        ))}
      </select>
    </label>
  );
}
