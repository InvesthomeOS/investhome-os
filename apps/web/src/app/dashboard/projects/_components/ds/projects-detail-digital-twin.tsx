'use client';

import { ProjectsDetailAmenities } from './projects-detail-amenities';
import { ProjectsDetailConstructionGallery } from './projects-detail-construction-gallery';
import { ProjectsDetailFloorPlans } from './projects-detail-floor-plans';
import { ProjectsDetailGallery } from './projects-detail-gallery';
import { ProjectsDetailLocation } from './projects-detail-location';
import { ProjectsDetailMarket } from './projects-detail-market';
import { ProjectsDetailMediaStats } from './projects-detail-media-stats';
import type {
  FloorPlanItem,
  LocationIntelligence,
  MediaStats,
  ProjectGalleryItem,
  AmenityItem,
} from './projects-detail-media-model';

/**
 * Digital Twin stack for Project Detail Overview.
 * Sections stay visible. Content comes from stored project records.
 */
export function ProjectsDetailDigitalTwin({
  locale,
  gallery,
  constructionPhotos,
  floorPlans,
  location,
  mediaStats,
  amenities,
  onRefreshLocation,
  refreshState,
}: {
  locale: string;
  gallery: ProjectGalleryItem[];
  constructionPhotos: ProjectGalleryItem[];
  floorPlans: FloorPlanItem[];
  location: LocationIntelligence;
  mediaStats: MediaStats;
  amenities: AmenityItem[];
  onRefreshLocation?: () => void;
  refreshState?: string | null;
}) {
  return (
    <div className="proj-detail-ds__twin" data-testid="projects-detail-digital-twin">
      <ProjectsDetailMediaStats stats={mediaStats} locale={locale} />
      <ProjectsDetailGallery items={gallery} locale={locale} />
      <ProjectsDetailConstructionGallery
        milestones={[]}
        photos={constructionPhotos}
        locale={locale}
      />
      <ProjectsDetailFloorPlans plans={floorPlans} locale={locale} />
      <ProjectsDetailLocation
        location={location}
        walkScores={[]}
        locale={locale}
        onRefresh={onRefreshLocation}
        refreshState={refreshState}
      />
      <ProjectsDetailAmenities amenities={amenities} locale={locale} />
      <ProjectsDetailMarket market={{ metrics: [] }} locale={locale} />
    </div>
  );
}
