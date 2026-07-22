/**
 * Location Intelligence — provider-agnostic contracts (UXR1 V2).
 * Mandatory on Project Detail + Unit Detail.
 * Do not hardcode a map vendor in product UI; inject via MapProvider.
 */

export type MapViewMode = 'roadmap' | 'satellite' | 'street' | 'hybrid';

export interface GeoPoint {
  lat: number;
  lng: number;
}

export type NearbyPlaceCategory =
  | 'schools'
  | 'restaurants'
  | 'cafes'
  | 'grocery'
  | 'metro'
  | 'parks'
  | 'universities'
  | 'hospitals';

export interface NearbyPlace {
  id: string;
  name: string;
  category: NearbyPlaceCategory;
  distanceMeters?: number;
  rating?: number;
  location: GeoPoint;
}

export interface MobilityScores {
  walk?: number | null;
  transit?: number | null;
  bike?: number | null;
}

export interface NeighborhoodSummary {
  /** AI-generated; always editable / overridable by humans */
  text: string;
  source: 'ai' | 'human' | 'hybrid';
  updatedAt?: string;
}

export interface LocationIntelligencePayload {
  center: GeoPoint;
  addressLabel?: string;
  nearby: NearbyPlace[];
  scores: MobilityScores;
  neighborhoodSummary?: NeighborhoodSummary;
}

export interface DirectionsRequest {
  origin: GeoPoint | string;
  destination: GeoPoint | string;
  mode?: 'driving' | 'walking' | 'transit' | 'bicycling';
}

export interface MapProvider {
  readonly id: string;
  readonly label: string;
  /** Interactive map mount — host supplies container element */
  renderMap?(container: HTMLElement, options: {
    center: GeoPoint;
    zoom?: number;
    mode?: MapViewMode;
  }): { destroy: () => void } | Promise<{ destroy: () => void }>;
  getNearbyPlaces?(center: GeoPoint, categories?: NearbyPlaceCategory[]): Promise<NearbyPlace[]>;
  getMobilityScores?(center: GeoPoint): Promise<MobilityScores>;
  getDirectionsUrl?(request: DirectionsRequest): string;
  openStreetView?(point: GeoPoint): void;
}

/** No-op stub so builds/tests can mount Location Intelligence UI without a vendor SDK. */
export const stubMapProvider: MapProvider = {
  id: 'stub',
  label: 'Map provider stub',
  renderMap(container, options) {
    container.setAttribute('data-map-stub', 'true');
    container.setAttribute('data-map-lat', String(options.center.lat));
    container.setAttribute('data-map-lng', String(options.center.lng));
    container.textContent = `Map stub · ${options.mode ?? 'roadmap'} · zoom ${options.zoom ?? 14}`;
    return { destroy: () => { container.replaceChildren(); } };
  },
  async getNearbyPlaces() {
    return [];
  },
  async getMobilityScores() {
    return { walk: null, transit: null, bike: null };
  },
  getDirectionsUrl(request) {
    const dest =
      typeof request.destination === 'string'
        ? request.destination
        : `${request.destination.lat},${request.destination.lng}`;
    return `https://maps.example/dir/?api=1&destination=${encodeURIComponent(dest)}`;
  },
  openStreetView() {
    /* no-op */
  },
};

export interface LocationIntelligenceService {
  getForProject(projectId: string): Promise<LocationIntelligencePayload>;
  getForUnit(unitId: string): Promise<LocationIntelligencePayload>;
  generateNeighborhoodSummary?(
    center: GeoPoint,
    nearby: NearbyPlace[],
  ): Promise<NeighborhoodSummary>;
}
