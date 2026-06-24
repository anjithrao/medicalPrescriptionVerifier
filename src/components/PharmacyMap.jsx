import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const userIcon = L.divIcon({
  className: '',
  html: '<div class="h-5 w-5 rounded-full border-2 border-white bg-clinic-cyan shadow-glow"></div>',
  iconSize: [20, 20],
  iconAnchor: [10, 10],
});

const storeIcon = L.divIcon({
  className: '',
  html: '<div class="h-4 w-4 rounded-full border-2 border-clinic-cyan bg-clinic-void shadow-glow"></div>',
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

/**
 * @param {{location: {lat: number, lon: number} | null, pharmacies: object[], selectedRoute: object | null, onRoute: (pharmacy: object) => void}} props
 */
export default function PharmacyMap({ location, pharmacies, selectedRoute, onRoute }) {
  const mapNodeRef = useRef(null);
  const mapRef = useRef(null);
  const markerLayerRef = useRef(null);
  const routeLayerRef = useRef(null);

  useEffect(() => {
    if (!mapNodeRef.current || mapRef.current) return;
    const map = L.map(mapNodeRef.current, { zoomControl: false }).setView([20.5937, 78.9629], 5);
    L.control.zoom({ position: 'bottomright' }).addTo(map);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    }).addTo(map);
    markerLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const layer = markerLayerRef.current;
    if (!map || !layer) return;
    layer.clearLayers();

    const bounds = [];
    if (location) {
      L.marker([location.lat, location.lon], { icon: userIcon }).addTo(layer).bindPopup('Your location');
      bounds.push([location.lat, location.lon]);
    }

    pharmacies.forEach((pharmacy) => {
      L.marker([pharmacy.lat, pharmacy.lon], { icon: storeIcon })
        .addTo(layer)
        .bindPopup(`<b>${pharmacy.name}</b><br>${Math.round(pharmacy.distance_m)} m away`)
        .on('click', () => onRoute(pharmacy));
      bounds.push([pharmacy.lat, pharmacy.lon]);
    });

    if (bounds.length) {
      map.fitBounds(bounds, { padding: [35, 35], maxZoom: 15 });
    }
  }, [location, pharmacies, onRoute]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (routeLayerRef.current) {
      routeLayerRef.current.remove();
      routeLayerRef.current = null;
    }
    if (selectedRoute?.geometry?.coordinates) {
      const latLngs = selectedRoute.geometry.coordinates.map((point) => [point[1], point[0]]);
      routeLayerRef.current = L.polyline(latLngs, { color: '#00e5cc', weight: 5, opacity: 0.95 }).addTo(map);
      map.fitBounds(routeLayerRef.current.getBounds(), { padding: [35, 35] });
    }
  }, [selectedRoute]);

  return (
    <div className="overflow-hidden rounded-3xl border border-clinic-cyan/20 bg-black/30 shadow-card">
      <div ref={mapNodeRef} className="h-[68vh] min-h-[460px] w-full" />
    </div>
  );
}
