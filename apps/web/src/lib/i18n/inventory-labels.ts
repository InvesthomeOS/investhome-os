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
  type ReservationRecordStatus,
  type ReservationStatus,
  type SalesStatus,
  type StatusCategory,
  type UsageType,
} from '@/lib/api/inventory';
import {
  type AssignmentRequestStatus,
  type AssignmentRequestType,
} from '@/lib/api/inventory-assignment';
import {
  type OwnershipType,
  type TransferRequestStatus,
  type TransferType,
} from '@/lib/api/inventory-ownership';
import {
  PRICE_REQUEST_STATUSES,
  PRICE_STATUSES,
  PRICE_TYPES,
  type PriceRequestStatus,
  type PriceStatus,
  type PriceType,
} from '@/lib/api/inventory-pricing';

export function useInventoryLabels() {
  const tAssetTypes = useTranslations('inventory.assetTypes');
  const tUsage = useTranslations('inventory.usageTypes');
  const tAvailability = useTranslations('inventory.availabilityStatus');
  const tReservation = useTranslations('inventory.reservationStatus');
  const tReservationRecord = useTranslations('inventory.reservationRecordStatus');
  const tSales = useTranslations('inventory.salesStatus');
  const tConstruction = useTranslations('inventory.constructionStatus');
  const tClosing = useTranslations('inventory.closingStatus');
  const tLeasing = useTranslations('inventory.leasingStatus');
  const tCategories = useTranslations('inventory.statusCategories');
  const tPriceTypes = useTranslations('inventory.pricing.priceTypes');
  const tPriceStatuses = useTranslations('inventory.pricing.priceStatuses');
  const tPriceRequestStatuses = useTranslations('inventory.pricing.requestStatuses');
  const tErrors = useTranslations('inventory.errors');
  const tPricingErrors = useTranslations('inventory.pricing.errors');
  const tAssignmentTypes = useTranslations('inventory.assignments.requestTypes');
  const tAssignmentStatuses = useTranslations('inventory.assignments.requestStatuses');
  const tOwnershipTypes = useTranslations('inventory.ownership.ownershipTypes');
  const tTransferTypes = useTranslations('inventory.ownership.transferTypes');
  const tTransferStatuses = useTranslations('inventory.ownership.requestStatuses');
  const tOwnershipStatuses = useTranslations('inventory.ownership.ownershipStatuses');

  const getAssetTypeLabel = (value: InventoryAssetType | string) =>
    tAssetTypes(value as InventoryAssetType);
  const getUsageTypeLabel = (value: UsageType | string) => tUsage(value as UsageType);
  const getAvailabilityLabel = (value: AvailabilityStatus | string) =>
    tAvailability(value as AvailabilityStatus);
  const getReservationLabel = (value: ReservationStatus | string) =>
    tReservation(value as ReservationStatus);
  const getReservationRecordLabel = (value: ReservationRecordStatus | string) =>
    tReservationRecord(value as ReservationRecordStatus);
  const getSalesLabel = (value: SalesStatus | string) => tSales(value as SalesStatus);
  const getConstructionLabel = (value: ConstructionStatus | string) =>
    tConstruction(value as ConstructionStatus);
  const getClosingLabel = (value: ClosingStatus | string) => tClosing(value as ClosingStatus);
  const getLeasingLabel = (value: LeasingStatus | string) => tLeasing(value as LeasingStatus);
  const getStatusCategoryLabel = (value: StatusCategory | string) =>
    tCategories(value as StatusCategory);
  const getPriceTypeLabel = (value: PriceType | string) => tPriceTypes(value as PriceType);
  const getPriceStatusLabel = (value: PriceStatus | string) => tPriceStatuses(value as PriceStatus);
  const getPriceRequestStatusLabel = (value: PriceRequestStatus | string) =>
    tPriceRequestStatuses(value as PriceRequestStatus);
  const getAssignmentRequestTypeLabel = (value: AssignmentRequestType | string) =>
    tAssignmentTypes(value as AssignmentRequestType);
  const getAssignmentRequestStatusLabel = (value: AssignmentRequestStatus | string) =>
    tAssignmentStatuses(value as AssignmentRequestStatus);
  const getOwnershipTypeLabel = (value: OwnershipType | string) =>
    tOwnershipTypes(value as OwnershipType);
  const getTransferTypeLabel = (value: TransferType | string) =>
    tTransferTypes(value as TransferType);
  const getTransferStatusLabel = (value: TransferRequestStatus | string) =>
    tTransferStatuses(value as TransferRequestStatus);
  const getOwnershipStatusLabel = (value: string) => tOwnershipStatuses(value as never);

  const getErrorLabel = (key: string): string => {
    const pricingKey = key.startsWith('inventory.pricing.errors.')
      ? key.replace('inventory.pricing.errors.', '')
      : null;
    if (pricingKey) {
      try {
        return tPricingErrors(pricingKey as never);
      } catch {
        return key;
      }
    }
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
  const priceTypeOptions = PRICE_TYPES.map((value) => ({ value, label: tPriceTypes(value) }));

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
    getReservationRecordLabel,
    getSalesLabel,
    getConstructionLabel,
    getClosingLabel,
    getLeasingLabel,
    getStatusCategoryLabel,
    getPriceTypeLabel,
    getPriceStatusLabel,
    getPriceRequestStatusLabel,
    getAssignmentRequestTypeLabel,
    getAssignmentRequestStatusLabel,
    getOwnershipTypeLabel,
    getTransferTypeLabel,
    getTransferStatusLabel,
    getOwnershipStatusLabel,
    getErrorLabel,
    assetTypeOptions,
    usageTypeOptions,
    availabilityOptions,
    reservationOptions,
    salesOptions,
    constructionOptions,
    closingOptions,
    leasingOptions,
    priceTypeOptions,
    statusCategoryOptions,
    statusOptionsByCategory,
  };
}
