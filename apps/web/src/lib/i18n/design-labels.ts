'use client';

import { useTranslations } from 'next-intl';
import { useMemo } from 'react';

import { DESIGN_STATUSES, DESIGN_TYPES, type DesignStatus, type DesignType, type FurnitureType } from '@/lib/api/design';

const TYPE_KEYS: Record<DesignType, string> = {
  colored_floor_plan: 'coloredFloorPlan',
  marketing_floor_plan: 'marketingFloorPlan',
  furniture_layout: 'furnitureLayout',
  material_plan: 'materialPlan',
  interior_concept: 'interiorConcept',
  exterior_concept: 'exteriorConcept',
  other: 'other',
};

const STATUS_KEYS: Record<DesignStatus, string> = {
  draft: 'draft',
  ready_for_review: 'readyForReview',
  revision_requested: 'revisionRequested',
  approved: 'approved',
  rejected: 'rejected',
  failed: 'failed',
  archived: 'archived',
};

const FURNITURE_TYPE_KEYS: Record<FurnitureType, string> = {
  sofa: 'sofa',
  armchair: 'armchair',
  coffee_table: 'coffeeTable',
  dining_table: 'diningTable',
  dining_chair: 'diningChair',
  bed: 'bed',
  bedside_table: 'bedsideTable',
  wardrobe: 'wardrobe',
  desk: 'desk',
  media_unit: 'mediaUnit',
  rug: 'rug',
  kitchen_island: 'kitchenIsland',
  stool: 'stool',
  vanity: 'vanity',
  bathtub: 'bathtub',
  shower: 'shower',
  toilet: 'toilet',
  other: 'other',
};

export function useDesignLabels() {
  const tTypes = useTranslations('design.types');
  const tStatuses = useTranslations('design.statuses');
  const tFurniture = useTranslations('design.furnitureTypes');

  const typeOptions = useMemo(
    () => DESIGN_TYPES.map((value) => ({ value, label: tTypes(TYPE_KEYS[value]) })),
    [tTypes],
  );

  const statusOptions = useMemo(
    () => DESIGN_STATUSES.map((value) => ({ value, label: tStatuses(STATUS_KEYS[value]) })),
    [tStatuses],
  );

  return {
    getTypeLabel: (type: DesignType | string) => {
      const key = TYPE_KEYS[type as DesignType];
      return key ? tTypes(key) : type;
    },
    getStatusLabel: (status: DesignStatus | string) => {
      const key = STATUS_KEYS[status as DesignStatus];
      return key ? tStatuses(key) : status;
    },
    getFurnitureTypeLabel: (type: FurnitureType | string) => {
      const key = FURNITURE_TYPE_KEYS[type as FurnitureType];
      return key ? tFurniture(key) : type;
    },
    typeOptions,
    statusOptions,
  };
}
