# 05 — Wireframe: Customer Profile

**Fidelity:** Low · **Route:** `/dashboard/customers/[id]`  
**Unifies:** Lead detail · CRM contact · Investor record (same person journey)

---

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Customers / Ada Yılmaz                                                     │
│                                                                              │
│  ┌────┐  Ada Yılmaz                    [Lead] [Buyer] [Investor?]            │
│  │ AV │  +90 … · ada@… · Owner: Selim  Lifecycle: Proposal sent              │
│  └────┘  Source: Meta Ads · Created: 12 Jun                                  │
│                                                                              │
│  [ Call ] [ WhatsApp ] [ Email ] [ Schedule ] [ Match units ] [ More ▾ ]     │
│                                                                              │
│  Overview │ Journey │ Opportunities │ Matches │ Docs │ Activity │ Details    │
├──────────────────────────────────────────────────────────────────────────────┤
│ OVERVIEW (default)                                                           │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────────┐  │
│  │ Next action         │  │ Active opportunity  │  │ Preference snapshot  │  │
│  │ Follow up proposal  │  │ North Towers A-1204 │  │ 2+1 · 8–12M TRY     │  │
│  │ Due: Today 16:00    │  │ Stage: Proposal     │  │ Marina preferred     │  │
│  │ [Done] [Snooze]     │  │ [Open in Sales]     │  │ [Edit]               │  │
│  └─────────────────────┘  └─────────────────────┘  └──────────────────────┘  │
│                                                                              │
│  Timeline (compact)                                                          │
│  • Today — Proposal PDF sent                                                 │
│  • Mon — Site visit completed                                                │
│  • 12 Jun — Lead created from campaign #482                                  │
│                                                                              │
│ DETAILS (collapsed by default)                                               │
│  ▸ Contact & identity                                                        │
│  ▸ Qualification & budget                                                    │
│  ▸ Investment profile (if investor path)                                     │
│  ▸ Attribution / UTM                                                         │
│  ▸ Compliance                                                                │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Journey strip (identity model)

```
Lead ──► Qualified ──► Opportunity ──► Reserved ──► Customer
                              └──► Investor path (optional badge)
```

- One URL per person.
- Badges reflect roles, not separate apps.
- “Convert to investor” is an action that adds role + fields — does not create a disconnected record in UI.

---

## Tabs

| Tab | Purpose |
|-----|---------|
| Overview | Next action, active deal, prefs |
| Journey | Lifecycle milestones |
| Opportunities | Linked sales deals (kanban deep links) |
| Matches | Inventory matching results + soft-hold |
| Docs | Proposals, KYC, contracts |
| Activity | Comms + notes |
| Details | Progressive disclosure field groups |

---

## List wireframe (Customers home)

```
Customers                          [Search] [Filters ▾] [+ Add]
[ All ] [ Leads ] [ Buyers ] [ Investors ] [ Customers ]

Cards/list toggle
• Ada Yılmaz — Proposal — Owner Selim — Follow-up today
• …
```
