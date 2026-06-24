import { useState } from 'react';
import { motion } from 'framer-motion';
import PharmacyMap from '../components/PharmacyMap.jsx';
import PharmacyList from '../components/PharmacyList.jsx';
import { getNearbyPharmacies, getRouteToPharmacy } from '../api.js';

function getCurrentPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Location is not supported in this browser.'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({ lat: position.coords.latitude, lon: position.coords.longitude }),
      () => reject(new Error('Location permission was denied or unavailable.')),
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 },
    );
  });
}

/**
 * @param {{onBack: () => void}} props
 */
export default function PharmaciesPage({ onBack }) {
  const [location, setLocation] = useState(null);
  const [pharmacies, setPharmacies] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [selectedPharmacyId, setSelectedPharmacyId] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleFindPharmacies() {
    setLoading(true);
    setError('');
    setSelectedRoute(null);
    setStatus('Requesting location...');
    try {
      const currentLocation = await getCurrentPosition();
      setLocation(currentLocation);
      setStatus('Scanning nearby medical stores...');
      const data = await getNearbyPharmacies(currentLocation, 2000);
      setPharmacies(data.pharmacies || []);
      setStatus((data.pharmacies || []).length ? `Found ${(data.pharmacies || []).length} stores within 2 km.` : 'No stores found within 2 km.');
    } catch (findError) {
      setError(findError.message);
      setStatus('');
    } finally {
      setLoading(false);
    }
  }

  async function handleRoute(pharmacy) {
    if (!location) return;
    setSelectedPharmacyId(pharmacy.id);
    setStatus(`Computing route to ${pharmacy.name}...`);
    setError('');
    try {
      const data = await getRouteToPharmacy(location, { lat: pharmacy.lat, lon: pharmacy.lon });
      setSelectedRoute({ ...data, pharmacy });
      setStatus(`Route ready: ${(data.distance_m / 1000).toFixed(2)} km, ${Math.max(1, Math.round(data.duration_s / 60))} min.`);
    } catch (routeError) {
      setSelectedRoute({ pharmacy, error: routeError.message });
      setError(routeError.message);
    }
  }

  return (
    <main className="relative z-10 min-h-screen px-4 pb-14 pt-24 md:px-8">
      <motion.section
        initial={{ opacity: 0, x: 100 }}
        animate={{ opacity: 1, x: 0 }}
        className="mx-auto max-w-7xl rounded-3xl border border-white/10 bg-white/[0.06] p-5 shadow-card backdrop-blur-2xl md:p-8"
      >
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.3em] text-clinic-cyan">OpenStreetMap Routing</p>
            <h2 className="mt-2 font-mono text-3xl font-bold">Nearby Pharmacies</h2>
            <p className="mt-2 max-w-2xl text-clinic-muted">Find medical stores within 2 km and draw the shortest OSRM driving route.</p>
          </div>
          <div className="flex gap-3">
            <button type="button" onClick={onBack} className="rounded-full border border-white/15 px-5 py-3 font-mono text-xs uppercase text-clinic-muted transition hover:border-clinic-cyan hover:text-clinic-cyan">
              Back
            </button>
            <button
              type="button"
              onClick={handleFindPharmacies}
              disabled={loading}
              className="rounded-full bg-clinic-cyan px-5 py-3 font-mono text-xs uppercase tracking-wide text-clinic-void transition hover:shadow-glow disabled:cursor-wait disabled:opacity-60"
            >
              {loading ? 'Scanning...' : 'Find Pharmacies Near Me'}
            </button>
          </div>
        </div>

        {(status || error) && (
          <div className={`mb-5 rounded-2xl border p-4 text-sm ${error ? 'border-clinic-red/40 bg-clinic-red/10 text-rose-100' : 'border-clinic-cyan/30 bg-clinic-cyan/10 text-clinic-cyan'}`}>
            {error || status}
          </div>
        )}

        <div className="grid gap-5 lg:grid-cols-[1.35fr_0.65fr]">
          <PharmacyMap location={location} pharmacies={pharmacies} selectedRoute={selectedRoute} onRoute={handleRoute} />
          <PharmacyList pharmacies={pharmacies} userLocation={location} selectedPharmacyId={selectedPharmacyId} onRoute={handleRoute} />
        </div>
      </motion.section>
    </main>
  );
}
