/**
 * Market Intelligence — provider-agnostic contracts (UXR1 V2).
 * Same engine for projects and units. NOT vendor-hardcoded (e.g. no Zillow lock-in).
 */

export type MarketEntityType = 'project' | 'unit' | 'neighborhood';

export interface MarketComp {
  id: string;
  kind: 'sale' | 'rental';
  addressLabel?: string;
  price: number;
  currency?: string;
  beds?: number;
  baths?: number;
  sqft?: number;
  closedAt?: string;
  distanceMeters?: number;
  sourceProviderId?: string;
}

export interface MarketTrendPoint {
  period: string;
  value: number;
}

export interface NeighborhoodStats {
  medianSalePrice?: number | null;
  medianRent?: number | null;
  pricePerSqft?: number | null;
  daysOnMarket?: number | null;
  inventoryCount?: number | null;
  vacancyRate?: number | null;
  yoyPriceChangePct?: number | null;
}

export interface MarketSummary {
  /** AI-generated; always human-editable */
  text: string;
  source: 'ai' | 'human' | 'hybrid';
  updatedAt?: string;
}

export interface MarketIntelligencePayload {
  entityType: MarketEntityType;
  entityId: string;
  compsSales: MarketComp[];
  compsRentals: MarketComp[];
  rentalTrend: MarketTrendPoint[];
  priceTrend: MarketTrendPoint[];
  neighborhoodStats: NeighborhoodStats;
  marketSummary?: MarketSummary;
}

export interface MarketDataProvider {
  readonly id: string;
  readonly label: string;
  fetchComps?(params: {
    entityType: MarketEntityType;
    entityId: string;
    kind: 'sale' | 'rental';
    limit?: number;
  }): Promise<MarketComp[]>;
  fetchTrends?(params: {
    entityType: MarketEntityType;
    entityId: string;
    metric: 'rent' | 'price';
  }): Promise<MarketTrendPoint[]>;
  fetchNeighborhoodStats?(params: {
    entityType: MarketEntityType;
    entityId: string;
  }): Promise<NeighborhoodStats>;
}

/** Empty stub — wire real providers behind this interface in Phase 2+. */
export const stubMarketDataProvider: MarketDataProvider = {
  id: 'stub',
  label: 'Market data provider stub',
  async fetchComps() {
    return [];
  },
  async fetchTrends() {
    return [];
  },
  async fetchNeighborhoodStats() {
    return {};
  },
};

export interface MarketIntelligenceService {
  getForProject(projectId: string): Promise<MarketIntelligencePayload>;
  getForUnit(unitId: string): Promise<MarketIntelligencePayload>;
  generateMarketSummary?(
    payload: Omit<MarketIntelligencePayload, 'marketSummary'>,
  ): Promise<MarketSummary>;
}
