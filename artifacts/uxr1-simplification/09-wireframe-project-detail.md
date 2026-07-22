# 09 — Wireframe: Project Detail

**Fidelity:** Low · **Route:** `/dashboard/projects/[projectId]`

---

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Projects / North Towers                                                     │
│ [ hero / cover strip ]                                                        │
│ North Towers · Construction · On track · Owner: PM Ayşe                       │
│ [ Edit ] [ Add unit ] [ Upload doc ]                                          │
│                                                                               │
│ Overview │ Units │ Timeline │ Team │ Docs │ Finance ▸ │ Advanced ▸            │
├──────────────────────────────────────────────────────────────────────────────┤
│ OVERVIEW                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │ Units sold   │ │ Available    │ │ Soft holds   │ │ Next mile-   │          │
│  │ 210 / 400    │ │ 120          │ │ 12           │ │ stone: Facade│          │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘          │
│                                                                               │
│  Progress ████████░░ 72%     Sales funnel (mini) → drill Sales filtered       │
│                                                                               │
│  Recent activity                                                              │
│  • Unit A-1204 reserved — Ada Yılmaz                                          │
│  • Milestone “Core complete” marked                                           │
│                                                                               │
│ UNITS tab → embeds Inventory cards filtered to this project                   │
│ TIMELINE tab → milestones (visual), not spreadsheet first                     │
│ FINANCE ▸ → progressive disclosure (budgets, ROI) — role gated                │
│ ADVANCED ▸ → geo, legal, ownership, projections                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Tab discipline

| Tab | Daily? | Notes |
|-----|--------|-------|
| Overview | Yes | One job: status of the project |
| Units | Yes | Card grid, not 6-status table |
| Timeline | Yes | Milestones |
| Team | Sometimes | People |
| Docs | Yes | Files |
| Finance | Restricted | Hide for pure sales roles if no permission |
| Advanced | Rare | Progressive disclosure |

Avoid packing construction + permits + costs + sales into one overwhelming default view.
