import { useTranslations } from 'next-intl';

import {
  AVAILABILITY_STATUSES,
  CLOSING_STATUSES,
  CONSTRUCTION_STATUSES,
  INVENTORY_ASSET_TYPES,
  LEASING_STATUSES,
  RESERVATION_STATUSES,
  SALES_STATUSES,
  STATUS_CATEGORIES,
  USAGE_TYPES,
  type AvailabilityStatus,
  type ClosingStatus,
  type ConstructionStatus,
  type InventoryAssetType,
  type LeasingStatus,
  type ReservationStatus,
  type SalesStatus,
  type StatusCategory,
  type UsageType,
} from '@/lib/api/inventory';

export function useInventoryLabels() {
  const tAssetTypes = useTranslations('inventory.assetTypes');
  const tUsage = useTranslations('inventory.usageTypes');
  const tAvailability = useTranslations('inventory.availabilityStatus');
  const tReservation = useTranslations('inventory.reservationStatus');
  const tSales = useTranslations('inventory.salesStatus');
  const tConstruction = useTranslations('inventory.constructionStatus');
  const tClosing = useTranslations('inventory.closingStatus');
  const tLeasing = useTranslations('inventory.leasingStatus');
  const tCategories = useTranslations('inventory.statusCategories');
  const tErrors = useTranslations('inventory.errors');

  const getAssetTypeLabel = (value: InventoryAssetType | string) =>
    tAssetTypes(value as InventoryAssetType);
  const getUsageTypeLabel = (value: UsageType | string) => tUsage(value as UsageType);
  const getAvailabilityLabel = (value: AvailabilityStatus | string) =>
    tAvailability(value as AvailabilityStatus);
  const getReservationLabel = (value: ReservationStatus | string) =>
    tReservation(value as ReservationStatus);
  const getSalesLabel = (value: SalesStatus | string) => tSales(value as SalesStatus);
  const getConstructionLabel = (value: ConstructionStatus | string) =>
    tConstruction(value as ConstructionStatus);
  const getClosingLabel = (value: ClosingStatus | string) => tClosing(value as ClosingStatus);
  const getLeasingLabel = (value: LeasingStatus | string) => tLeasing(value as LeasingStatus);
  const getStatusCategoryLabel = (value: StatusCategory | string) =>
    tCategories(value as StatusCategory);

  const getErrorLabel = (key: string): string => {
    const normalized = key.startsWith('inventory.errors.') ? key.replace('inventory.errors.', '') : key;
    try {
      return tErrors(normalized as never);
    } catch {
      return key;
    }
  };

  const assetTypeOptions = INVENTORY_ASSET_TYPES.map((value) => ({
    value,
    label: tAssetTypes(value),
  }));
  const usageTypeOptions = USAGE_TYPES.map((value) => ({ value, label: tUsage(value) }));
  const availabilityOptions = AVAILABILITY_STATUSES.map((value) => ({
    value,
    label: tAvailability(value),
  }));
  const reservationOptions = RESERVATION_STATUSES.map((value) => ({
    value,
    label: tReservation(value),
  }));
  const salesOptions = SALES_STATUSES.map((value) => ({ value, label: tSales(value) }));
  const constructionOptions = CONSTRUCTION_STATUSES.map((value) => ({
    value,
    label: tConstruction(value),
  }));
  const closingOptions = CLOSING_STATUSES.map((value) => ({ value, label: tClosing(value) }));
  const leasingOptions = LEASING_STATUSES.map((value) => ({ value, label: tLeasing(value) }));
  const statusCategoryOptions = STATUS_CATEGORIES.map((value) => ({
    value,
    label: tCategories(value),
  }));

  const statusOptionsByCategory: Record<StatusCategory, { value: string; label: string }[]> = {
    availability: availabilityOptions,
    reservation: reservationOptions,
    sales: salesOptions,
    construction: constructionOptions,
    closing: closingOptions,
    leasing: leasingOptions,
  };

  return {
    getAssetTypeLabel,
    getUsageTypeLabel,
    getAvailabilityLabel,
    getReservationLabel,
    getSalesLabel,
    getConstructionLabel,
    getClosingLabel,
    getLeasingLabel,
    getStatusCategoryLabel,
    getErrorLabel,
    assetTypeOptions,
    usageTypeOptions,
    availabilityOptions,
    reservationOptions,
    salesOptions,
    constructionOptions,
    closingOptions,
    leasingOptions,
    statusCategoryOptions,
    statusOptionsByCategory,
  };
}
