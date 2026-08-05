'use client';

import { useMemo } from 'react';

import { getProjectProposalMediaBundle } from './projects-detail-proposal-bundle';
import { ProjectsDetailAmenities } from './projects-detail-amenities';
import { ProjectsDetailConstructionGallery } from './projects-detail-construction-gallery';
import { ProjectsDetailFloorPlans } from './projects-detail-floor-plans';
import { ProjectsDetailGallery } from './projects-detail-gallery';
import { ProjectsDetailLocation } from './projects-detail-location';
import { ProjectsDetailMarket } from './projects-detail-market';
import { ProjectsDetailMediaStats } from './projects-detail-media-stats';

/**
 * Digital Twin expansion stack for Project Detail Overview.
 * Full-width sections above the existing overview widget grid.
 * Data comes from getProjectProposalMediaBundle for Proposal Engine reuse.
 */
export function ProjectsDetailDigitalTwin({
  projectId,
  locale,
}: {
  projectId: string;
  locale: string;
}) {
  const bundle = useMemo(() => getProjectProposalMediaBundle(projectId), [projectId]);

  return (
    <div className="proj-detail-ds__twin" data-testid="projects-detail-digital-twin">
      <ProjectsDetailMediaStats stats={bundle.mediaStats} locale={locale} />
      <ProjectsDetailGallery items={bundle.gallery} locale={locale} />
      <ProjectsDetailConstructionGallery
        milestones={bundle.constructionGallery}
        locale={locale}
      />
      <ProjectsDetailFloorPlans plans={bundle.floorPlans} locale={locale} />
      <ProjectsDetailLocation
        location={bundle.location}
        walkScores={bundle.walkScores}
        locale={locale}
      />
      <ProjectsDetailAmenities amenities={bundle.amenities} locale={locale} />
      <ProjectsDetailMarket market={bundle.market} locale={locale} />
    </div>
  );
}
