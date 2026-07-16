'use client';

import { useTranslations } from 'next-intl';

import type { CompareAssetItem } from '@/lib/api/sales-inventory-matching';

interface InventoryCompareViewProps {
  items: CompareAssetItem[];
}

export function InventoryCompareView({ items }: InventoryCompareViewProps) {
  const t = useTranslations('salesInventoryMatching');
  const fields: Array<keyof CompareAssetItem> = [
    'display_id',
    'asset_type',
    'bedrooms',
    'bathrooms',
    'interior_area_sqft',
    'availability_status',
    'list_price',
    'project_name',
  ];

  return (
    <div className="inventory-compare-view">
      <table>
        <thead>
          <tr>
            <th>{t('compare.field')}</th>
            {items.map((item) => (
              <th key={item.asset_id}>{item.display_id ?? item.system_code}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {fields.map((field) => {
            const values = items.map((item) => String(item[field] ?? '—'));
            const allSame = values.every((v) => v === values[0]);
            return (
              <tr key={field} className={allSame ? '' : 'inventory-compare-diff'}>
                <td>{t(`compare.${field}` as 'compare.field')}</td>
                {items.map((item) => (
                  <td key={`${item.asset_id}-${field}`}>{String(item[field] ?? '—')}</td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
