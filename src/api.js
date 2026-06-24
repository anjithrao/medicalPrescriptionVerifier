async function parseJsonResponse(response, fallbackMessage) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || fallbackMessage);
  }
  return data;
}

/**
 * @param {File} imageFile
 * @returns {Promise<object>}
 */
export async function processPrescription(imageFile) {
  const formData = new FormData();
  formData.append('image', imageFile);
  const response = await fetch('/process', { method: 'POST', body: formData });
  return parseJsonResponse(response, 'Unable to process prescription.');
}

/**
 * @param {Array<{name: string, uses: string, side_effects: string}>} items
 * @param {string} targetLanguage
 * @returns {Promise<object>}
 */
export async function translateReferences(items, targetLanguage) {
  const response = await fetch('/translate_references', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items, target_language: targetLanguage }),
  });
  return parseJsonResponse(response, 'Translation failed.');
}

/**
 * @param {{lat: number, lon: number}} location
 * @param {number} radiusM
 * @returns {Promise<object>}
 */
export async function getNearbyPharmacies(location, radiusM = 2000) {
  const response = await fetch('/nearby_pharmacies', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...location, radius_m: radiusM }),
  });
  return parseJsonResponse(response, 'Unable to find nearby pharmacies.');
}

/**
 * @param {{lat: number, lon: number}} start
 * @param {{lat: number, lon: number}} end
 * @returns {Promise<object>}
 */
export async function getRouteToPharmacy(start, end) {
  const response = await fetch('/route_to_pharmacy', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ start, end }),
  });
  return parseJsonResponse(response, 'Unable to find a route.');
}
