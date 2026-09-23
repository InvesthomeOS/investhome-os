export type MatchViewMode = 'card' | 'table';

export type MatchAiActionKey =
  | 'best'
  | 'roi'
  | 'rent'
  | 'safest'
  | 'newProjects';

export type MatchStatusKey = 'construction' | 'ready' | 'preSales' | 'completed';

export type MatchCustomer = {
  id: string;
  displayName: string;
  email: string;
  phone: string;
  verified: boolean;
  profileHref: string;
  initials: string;
  photoTone: 'warm' | 'cool' | 'neutral';
  budget: string;
  investmentGoalKey: 'rentalIncome' | 'appreciation' | 'balanced';
  preferredAreas: string;
  roiTarget: string;
  riskProfileKey: 'low' | 'medium' | 'high';
  languageKey: 'turkish' | 'english';
  nationalityKey: 'turkey' | 'usa' | 'other';
  investmentHorizonKey: '1-3y' | '3-5y' | '5-10y';
  financingKey: 'mortgageEligible' | 'cash' | 'mixed';
  investorTypeKey: 'individual' | 'corporate';
  preferredUnit: string;
};

export type MatchCard = {
  id: string;
  projectName: string;
  location: string;
  developer: string;
  price: string;
  unitType: string;
  area: string;
  roi: string;
  monthlyRent: string;
  monthlyCashFlow: string;
  deliveryDate: string;
  status: MatchStatusKey;
  matchScore: number;
  scene: 'marina' | 'ocean' | 'park' | 'sunset' | 'sky' | 'garden';
  whyKeys: Array<
    | 'withinBudget'
    | 'highRentalYield'
    | 'preferredArea'
    | 'strongCashFlow'
    | 'nearTargetRoi'
    | 'developerTrackRecord'
    | 'stableMarket'
    | 'mortgageFriendly'
    | 'unitTypeMatch'
    | 'growthCorridor'
    | 'readyDelivery'
    | 'nearBudgetCeiling'
  >;
  favorite?: boolean;
};

export type MatchRiskAlert = {
  id: string;
  tone: 'warning' | 'info';
  titleKey: 'deliveryHorizon' | 'currencyExposure';
  bodyKey: 'deliveryHorizonBody' | 'currencyExposureBody';
};

export type MatchDocument = {
  id: string;
  nameKey: 'investmentPitch' | 'financialAnalysis' | 'comparisonSheet';
  metaKey: 'pdfMeta' | 'xlsxMeta';
};

export type MatchActivity = {
  id: string;
  titleKey: 'aiAnalysisCompleted' | 'projectsAdded' | 'preferenceUpdated';
  timeKey: 'hoursAgo2' | 'yesterday' | 'daysAgo3';
};

export type MatchWorkspacePreview = {
  customer: MatchCustomer;
  matches: MatchCard[];
  totalMatches: number;
  recommendationId: string;
  recommendationSummaryKey: 'marinaHeights';
  riskAlerts: MatchRiskAlert[];
  documents: MatchDocument[];
  activities: MatchActivity[];
};
