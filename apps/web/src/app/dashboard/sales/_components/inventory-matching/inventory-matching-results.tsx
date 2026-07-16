'use client';

import type { InventorySearchResultItem, InventoryMatch } from '@/lib/api/sales-inventory-matching';

interface InventoryMatchingResultsProps {
  items: InventorySearchResultItem[];
  matches: InventoryMatch[];
}

export function InventoryMatchingResults({ items }: InventoryMatchingResultsProps) {
  return (
    <ul>
      {items.map((item) => (
        <li key={item.asset_id}>{item.display_id ?? item.system_code}</li>
      ))}
    </ul>
  );
}
