/**
 * Stored-place map model. The browser loads only the Maps JavaScript API.
 * It must not call Geocoding or Places.
 */

export const LOCATION_MAP_CATEGORIES = [
  'transit',
  'grocery',
  'food',
  'parks',
  'education',
  'healthcare',
  'fitness',
  'retail',
  'landmarks',
];

const MAPS_JS = 'https://maps.googleapis.com/maps/api/js';
const FORBIDDEN = ['/maps/api/place', '/maps/api/geocode', 'places.googleapis.com'];

function finiteCoordinate(value, min, max) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) return null;
  return value;
}

/** Next.js inlines this direct process.env.NEXT_PUBLIC_* access at web image build time. */
export function browserMapsKey(value = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY) {
  return typeof value === 'string' ? value.trim() : '';
}

export function googleMapsScriptUrl(key) {
  const token = typeof key === 'string' ? key.trim() : '';
  if (!token) throw new Error('missing maps browser key');
  const url = new URL(MAPS_JS);
  url.searchParams.set('key', token);
  url.searchParams.set('v', 'weekly');
  const href = url.toString();
  if (FORBIDDEN.some((part) => href.includes(part)) || href.includes('libraries=')) {
    throw new Error('maps script must not request places or geocoding');
  }
  return href;
}

export function isProviderRequest(url) {
  const value = String(url);
  return FORBIDDEN.some((part) => value.includes(part));
}

export function projectMapCenter(location) {
  const lat = finiteCoordinate(location?.lat, -90, 90);
  const lng = finiteCoordinate(location?.lng, -180, 180);
  if (lat == null || lng == null) return null;
  return { lat, lng };
}

export function nearbyPlacesForCategory(places, category = 'all') {
  const rows = Array.isArray(places) ? places : [];
  if (category === 'all') return rows.filter((place) => LOCATION_MAP_CATEGORIES.includes(place?.kindEn));
  if (!LOCATION_MAP_CATEGORIES.includes(category)) return [];
  return rows.filter((place) => place?.kindEn === category);
}

export function nearbyMarkers(places, category = 'all') {
  return nearbyPlacesForCategory(places, category).filter((place) => {
    const lat = finiteCoordinate(place?.lat, -90, 90);
    const lng = finiteCoordinate(place?.lng, -180, 180);
    return lat != null && lng != null;
  });
}

export function markerInfo(place, locale = 'en') {
  const name = locale === 'tr' ? place?.nameTr || place?.nameEn || '' : place?.nameEn || place?.nameTr || '';
  const address = typeof place?.address === 'string' ? place.address.trim() : '';
  return {
    name,
    category: place?.kindEn || '',
    address,
  };
}

let mapsPromise = null;

export function loadGoogleMaps(key) {
  if (typeof window === 'undefined') return Promise.reject(new Error('maps require a browser'));
  if (window.google?.maps) return Promise.resolve(window.google);
  if (mapsPromise) return mapsPromise;
  const href = googleMapsScriptUrl(key);
  mapsPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.async = true;
    script.dataset.ihMaps = '1';
    script.src = href;
    script.onload = () => {
      if (window.google?.maps) resolve(window.google);
      else reject(new Error('maps unavailable'));
    };
    script.onerror = () => reject(new Error('maps load failed'));
    document.head.appendChild(script);
  }).catch((error) => {
    mapsPromise = null;
    throw error;
  });
  return mapsPromise;
}
