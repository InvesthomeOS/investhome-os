'use client';

import { ProjectsDetailAmenities } from './projects-detail-amenities';
import { ProjectsDetailGallery } from './projects-detail-gallery';
import { ProjectsDetailLocation } from './projects-detail-location';
import { ProjectsDetailMediaStats } from './projects-detail-media-stats';
import type {
  LocationIntelligence,
  MediaStats,
  ProjectGalleryItem,
  AmenityItem,
} from './projects-detail-media-model';

/**
 * Project overview media. Empty sections stay hidden.
 * Images come from linked project media, never from operational documents.
 */
export function ProjectsDetailDigitalTwin({
  locale,
  gallery,
  location,
  mediaStats,
  amenities,
  onRefreshLocation,
  refreshState,
  refreshError,
}: {
  locale: string;
  gallery: ProjectGalleryItem[];
  location: LocationIntelligence;
  mediaStats: MediaStats;
  amenities: AmenityItem[];
  onRefreshLocation: () => void;
  refreshState?: string | null;
  refreshError?: string | null;
}) {
  const hasVisuals =
    mediaStats.photos + mediaStats.videos + mediaStats.renderings + mediaStats.floorPlans > 0;
  const hasAddress = Boolean(location.addressEn || location.addressTr);
  const hasCoordinates = location.lat != null && location.lng != null;

  return (
    <div className="proj-detail-ds__twin" data-testid="projects-detail-digital-twin">
      {hasVisuals ? <ProjectsDetailMediaStats stats={mediaStats} locale={locale} /> : null}
      {gallery.length > 0 ? <ProjectsDetailGallery items={gallery} locale={locale} /> : null}
      {hasAddress || hasCoordinates ? (
        <ProjectsDetailLocation
          location={location}
          walkScores={[]}
          locale={locale}
          onRefresh={onRefreshLocation}
          refreshState={refreshState}
          refreshError={refreshError}
        />
      ) : null}
      {amenities.length > 0 ? (
        <ProjectsDetailAmenities amenities={amenities} locale={locale} />
      ) : null}
    </div>
  );
}
