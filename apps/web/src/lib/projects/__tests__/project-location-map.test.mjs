/**
 * Stored location map contract.
 * Run: node --test src/lib/projects/__tests__/project-location-map.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  LOCATION_MAP_CATEGORIES,
  browserMapsKey,
  googleMapsScriptUrl,
  isProviderRequest,
  markerInfo,
  nearbyMarkers,
  nearbyPlacesForCategory,
  projectMapCenter,
} from '../project-location-map.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const webSrc = join(here, '../../..');

function read(rel) {
  return readFileSync(join(webSrc, rel), 'utf8');
}

const project = { lat: 38.9321, lng: -77.0365 };
const places = [
  {
    id: 'metro-1',
    nameEn: 'Columbia Heights Station',
    nameTr: 'Columbia Heights Station',
    kindEn: 'transit',
    lat: 38.9284,
    lng: -77.0326,
    address: '14th St NW, Washington, DC',
  },
  {
    id: 'cafe-1',
    nameEn: 'Tryst',
    nameTr: 'Tryst',
    kindEn: 'food',
    lat: 38.9302,
    lng: -77.0381,
    address: null,
  },
  {
    id: 'park-1',
    nameEn: 'Meridian Hill',
    nameTr: 'Meridian Hill',
    kindEn: 'parks',
    lat: 38.921,
    lng: -77.036,
    address: '16th St NW',
  },
];

describe('project location map', () => {
  it('centers on the stored project coordinates', () => {
    assert.deepEqual(projectMapCenter(project), { lat: 38.9321, lng: -77.0365 });
    assert.equal(projectMapCenter({ lat: null, lng: null }), null);
  });

  it('turns stored nearby places into markers and filters by category', () => {
    assert.deepEqual(
      nearbyMarkers(places, 'all').map((place) => place.id),
      ['metro-1', 'cafe-1', 'park-1'],
    );
    assert.deepEqual(
      nearbyMarkers(places, 'food').map((place) => place.id),
      ['cafe-1'],
    );
    assert.deepEqual(nearbyMarkers(places, 'healthcare'), []);
    assert.deepEqual(
      nearbyMarkers([{ ...places[0], lat: null, lng: null }], 'transit'),
      [],
    );
    assert.deepEqual(
      nearbyPlacesForCategory(places, 'parks').map((place) => place.id),
      ['park-1'],
    );
    assert.deepEqual(LOCATION_MAP_CATEGORIES, [
      'transit',
      'grocery',
      'food',
      'parks',
      'education',
      'healthcare',
      'fitness',
      'retail',
      'landmarks',
    ]);
  });

  it('shows name, category, and address from stored fields', () => {
    assert.deepEqual(markerInfo(places[0], 'en'), {
      name: 'Columbia Heights Station',
      category: 'transit',
      address: '14th St NW, Washington, DC',
    });
    assert.equal(markerInfo(places[1], 'en').address, '');
  });

  it('loads only the Maps JavaScript API and never Places or Geocoding', () => {
    const url = googleMapsScriptUrl('test-browser-key');
    assert.match(url, /^https:\/\/maps\.googleapis\.com\/maps\/api\/js\?/);
    assert.match(url, /[?&]key=test-browser-key(?:&|$)/);
    assert.match(url, /[?&]v=weekly(?:&|$)/);
    assert.equal(url.includes('libraries='), false);
    assert.equal(isProviderRequest(url), false);
    assert.equal(isProviderRequest('https://maps.googleapis.com/maps/api/place/nearbysearch/json'), true);
    assert.equal(isProviderRequest('https://maps.googleapis.com/maps/api/geocode/json'), true);
    assert.equal(isProviderRequest('https://places.googleapis.com/v1/places:searchNearby'), true);
    assert.throws(() => googleMapsScriptUrl(''), /missing maps browser key/);
  });

  it('treats a missing browser key as unavailable and ignores the server key name', () => {
    assert.equal(browserMapsKey(''), '');
    assert.equal(browserMapsKey('  '), '');
    assert.equal(browserMapsKey(undefined), '');
    assert.equal(browserMapsKey('browser-key'), 'browser-key');

    const map = read('lib/projects/project-location-map.mjs').replace(
      /const FORBIDDEN = \[[\s\S]*?\];/,
      '',
    );
    const view = read('app/dashboard/projects/_components/ds/projects-detail-location-map.tsx');
    const location = read('app/dashboard/projects/_components/ds/projects-detail-location.tsx');
    const overlay = read('app/dashboard/projects/_components/ds/projects-detail-overview-live.ts');
    const sources = [map, view, location];
    for (const source of sources) {
      assert.equal(source.includes('GOOGLE_MAPS_API_KEY'), source.includes('NEXT_PUBLIC_GOOGLE_MAPS_API_KEY'));
      assert.doesNotMatch(source, /\/maps\/api\/place|\/maps\/api\/geocode|places\.googleapis\.com/);
    }
    assert.match(view, /data-testid="project-location-map"/);
    assert.match(view, /data-testid="project-location-map-fallback"/);
    assert.match(view, /browserMapsKey\(/);
    assert.doesNotMatch(location, /map-rings|map-grid|map-pin/);
    assert.match(overlay, /lat: place\.latitude/);
    assert.match(overlay, /lng: place\.longitude/);
    assert.match(overlay, /address: place\.address/);
  });
});
