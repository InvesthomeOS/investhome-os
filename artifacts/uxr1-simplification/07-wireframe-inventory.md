# 07 — Wireframe: Inventory

**Fidelity:** Low · **Route:** `/dashboard/inventory`  
**Primary:** Visual cards · Table = power toggle

---

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Inventory            [Cards ●] [Table]     Project ▾  Building ▾  Status ▾   │
│ Availability summary: Available 120 · Reserved 34 · Sold 210 · Hold 12       │
│ (Donut optional mini — same contract as Dashboard Unit Availability)         │
├──────────────┬───────────────────────────────────────────────────────────────┤
│ Projects     │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│ ▸ North Tow. │  │[ image ] │ │[ image ] │ │[ image ] │ │[ image ] │          │
│   B1         │  │ A-1204   │ │ A-1208   │ │ B-402    │ │ B-410    │          │
│   B2         │  │ 2+1 · 95m│ │ 2+1 · 98m│ │ 1+1 · 62m│ │ 3+1 ·140m│          │
│ ▸ Marina     │  │ 9.2M TRY │ │ 9.8M TRY │ │ 6.1M TRY │ │ 14.2M   │          │
│              │  │ AVAILABLE│ │ HOLD     │ │RESERVED  │ │ SOLD     │          │
│ Floors       │  │[Match][…]│ │[Release] │ │[View]    │ │[View]    │          │
│  10 11 12    │  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│              │                                                               │
│              │  Primary status = one chip. Secondary (construction/closing)  │
│              │  only on card hover or detail drawer.                         │
└──────────────┴───────────────────────────────────────────────────────────────┘
```

---

## Unit drawer (simplified)

```
A-1204 · North Towers
Primary status: Available
Price: 9.2M (approved)
[ Soft hold ] [ Reserve ] [ Edit ]

Overview | Pricing | History | Docs | Advanced ▸
```

Advanced: legal id, orientation, view, multi-area, release/delivery, leasing/construction/closing statuses.

---

## Matching entry points

1. From Sales opportunity → Match panel (filters prefilled).
2. From Inventory card → “Match to customer”.
3. From Customer Matches tab.
