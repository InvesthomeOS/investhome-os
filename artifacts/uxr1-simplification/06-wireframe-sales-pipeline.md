# 06 — Wireframe: Sales Pipeline

**Fidelity:** Low · **Route:** `/dashboard/sales`  
**Primary UI:** Kanban · List secondary

---

## Stages (columns)

```
 New │ Qualified │ Meeting │ Proposal │ Soft hold │ Reservation │ Deposit │ Contract │ Won │ Lost
```

(Collapsed on small screens into horizontal scroll; Won/Lost may sit in “Closed” filter to reduce width.)

---

## Board layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Sales                          [Board ●] [List]     [Owner ▾] [Project ▾]    │
│ KPIs: Open 86 · Overdue 8 · Soft holds 5 · Closing this week 3               │
├──────────────────────────────────────────────────────────────────────────────┤
│ ┌──── New ────┐ ┌─ Qualified ┐ ┌─ Meeting ─┐ ┌ Proposal ┐ ┌ Soft hold ┐ …  │
│ │ ┌─────────┐ │ │ ┌────────┐ │ │           │ │┌────────┐│ │┌─────────┐│    │
│ │ │Ada Y.   │ │ │ │M. Kaya │ │ │           │ ││…       ││ ││Unit A12 ││    │
│ │ │8–12M    │ │ │ │Budget? │ │ │           │ ││PDF sent││ ││expires  ││    │
│ │ │Meta     │ │ │ │[Match] │ │ │           │ │└────────┘│ │└─────────┘│    │
│ │ └─────────┘ │ │ └────────┘ │ │           │ │          │ │           │    │
│ │ +2 more     │ │            │ │           │ │          │ │           │    │
│ └─────────────┘ └────────────┘ └───────────┘ └──────────┘ └───────────┘    │
├──────────────────────────────────────────────────────────────────────────────┤
│ DRAWER (card click)                                                          │
│  Opportunity · Ada Yılmaz                                                    │
│  Stage: Proposal sent → [Change stage]                                       │
│  Customer: [Open profile]                                                    │
│  Match: 3 units · [Open matching]                                            │
│  Next follow-up: Today · Notes · Docs                                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Matching workflow (panel)

```
┌─ Match inventory ─────────────────────────────────────────────┐
│ Filters: Project · Beds · Budget · Availability               │
│ ┌────────┐ ┌────────┐ ┌────────┐                              │
│ │ A-1204 │ │ A-1208 │ │ B-402  │   visual mini-cards          │
│ │ 2+1    │ │ 2+1    │ │ 1+1    │                              │
│ │ 9.2M   │ │ 9.8M   │ │ 6.1M   │                              │
│ │[Hold]  │ │[Hold]  │ │[View]  │                              │
│ └────────┘ └────────┘ └────────┘                              │
│ Empty: “No units match — widen filters”                       │
└───────────────────────────────────────────────────────────────┘
```

---

## Stage change rules (UX)

- Soft hold / Reservation / Deposit / Contract may open confirmation modal (existing pattern).
- Lost requires reason.
- Won requires closing checklist handoff (finance/docs) — not silent.
