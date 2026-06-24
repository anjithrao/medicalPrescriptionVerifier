function formatDistance(meters) {
  const value = Number(meters || 0);
  return value >= 1000 ? `${(value / 1000).toFixed(2)} km` : `${Math.round(value)} m`;
}

function directionsUrl(userLocation, pharmacy) {
  if (!userLocation || !pharmacy) return 'https://www.openstreetmap.org';
  const start = `${userLocation.lat},${userLocation.lon}`;
  const end = `${pharmacy.lat},${pharmacy.lon}`;
  return `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${encodeURIComponent(start)};${encodeURIComponent(end)}`;
}

/**
 * @param {{pharmacies: object[], userLocation: {lat: number, lon: number} | null, selectedPharmacyId?: string, onRoute: (pharmacy: object) => void}} props
 */
export default function PharmacyList({ pharmacies, userLocation, selectedPharmacyId, onRoute }) {
  if (!pharmacies.length) {
    return (
      <aside className="rounded-3xl border border-white/10 bg-white/[0.05] p-5 text-clinic-muted">
        Nearby stores will appear here after location access is granted.
      </aside>
    );
  }

  return (
    <aside className="max-h-[68vh] overflow-y-auto rounded-3xl border border-white/10 bg-white/[0.05] p-4 shadow-card backdrop-blur-xl">
      <div className="mb-4 font-mono text-xs uppercase tracking-[0.25em] text-clinic-cyan">Stores Found</div>
      <div className="space-y-3">
        {pharmacies.map((pharmacy, index) => (
          <article
            key={pharmacy.id}
            className={`rounded-2xl border p-4 transition hover:border-clinic-cyan hover:bg-clinic-cyan/5 ${
              selectedPharmacyId === pharmacy.id ? 'border-clinic-cyan bg-clinic-cyan/10 shadow-glow' : 'border-white/10 bg-black/20'
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-mono text-sm font-bold text-clinic-bone">{index + 1}. {pharmacy.name}</h3>
                <p className="mt-1 text-xs leading-5 text-clinic-muted">{pharmacy.address || 'Address not available'}</p>
              </div>
              <span className="shrink-0 rounded-full bg-clinic-cyan/10 px-3 py-1 font-mono text-[10px] text-clinic-cyan">
                {formatDistance(pharmacy.distance_m)}
              </span>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => onRoute(pharmacy)}
                className="rounded-full bg-clinic-cyan px-4 py-2 font-mono text-xs uppercase text-clinic-void transition hover:shadow-glow"
              >
                Get Route
              </button>
              <a
                href={directionsUrl(userLocation, pharmacy)}
                target="_blank"
                rel="noreferrer"
                className="rounded-full border border-white/15 px-4 py-2 font-mono text-xs uppercase text-clinic-muted transition hover:border-clinic-cyan hover:text-clinic-cyan"
              >
                Open in Maps
              </a>
            </div>
          </article>
        ))}
      </div>
    </aside>
  );
}
