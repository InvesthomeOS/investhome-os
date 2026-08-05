/**
 * Proposal Engine readiness export.
 *
 * Future "Generate Proposal" flows should import from this module (or the
 * underlying media model) and consume structured Digital Twin sections
 * without manual media selection.
 *
 * Consumable modules (see PROPOSAL_MEDIA_MODULE_KEYS):
 * - mediaStats
 * - gallery (Project Gallery)
 * - constructionGallery
 * - floorPlans
 * - location (Location Intelligence)
 * - walkScores
 * - amenities (Neighborhood Amenities)
 * - market (Market Intelligence)
 */

export {
  getProjectProposalMediaBundle,
  PROPOSAL_MEDIA_MODULE_KEYS,
  localizedCaption,
  localizedName,
  localizedTitle,
  localizedValue,
  type AmenityCategory,
  type AmenityItem,
  type ConstructionGalleryMilestone,
  type ConstructionPhaseKey,
  type FloorPlanItem,
  type FloorPlanType,
  type GalleryCategory,
  type InspectionStatus,
  type LocationIntelligence,
  type MarketIntelligence,
  type MarketMetric,
  type MarketMetricKey,
  type MediaStats,
  type ProjectGalleryItem,
  type ProjectProposalMediaBundle,
  type ProposalMediaModuleKey,
  type WalkScoreBadgeKey,
  type WalkScoreItem,
  type WalkScoreKind,
} from './projects-detail-media-model';
