# 08 — Wireframe: Project Cards

**Fidelity:** Low · **Route:** `/dashboard/projects`  
**Primary:** Visual card grid

---

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Projects                    [Cards ●] [List]   Status ▾  Priority ▾  [+ New] │
├──────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐    │
│ │ [ cover image     ] │  │ [ cover           ] │  │ [ cover           ] │    │
│ │                     │  │                     │  │                     │    │
│ │ North Towers        │  │ Marina Residences   │  │ Garden Villas       │    │
│ │ Construction · High │  │ Sales · Medium      │  │ Planning · Low      │    │
│ │ Units 210/400 sold  │  │ Units 40/120        │  │ Units —            │    │
│ │ ████████░░ 72%      │  │ ████░░░░░ 41%       │  │ ██░░░░░░░ 15%       │    │
│ │ Health: On track    │  │ Health: At risk     │  │ Health: Early       │    │
│ └─────────────────────┘  └─────────────────────┘  └─────────────────────┘    │
│                                                                              │
│ Empty: “No projects yet — create first project”                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Card fields (visible)

- Cover / placeholder
- Project name
- Phase / status + priority
- Unit progress (sold or released vs total) when known
- Health badge
- Optional: city / delivery year

## Hidden on card (open detail)

Financial projections, lat/long, ownership, dense cost breakdowns.
