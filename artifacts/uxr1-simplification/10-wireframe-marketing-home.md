# 10 — Wireframe: Marketing Home

**Fidelity:** Low · **Route:** `/dashboard/marketing`  
**Goal:** Replace 30-item marketing rail with a calm production home.

---

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Marketing                                                                     │
│ [ Campaigns ] [ Audiences ] [ Content Studio → ] [ Calendar ] [ Advanced ▾ ]  │
│                                                                               │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐                   │
│ │ Active     │ │ Leads in   │ │ Content    │ │ Spend (7d) │                   │
│ │ campaigns  │ │ period     │ │ shipped    │ │ (if finance│                   │
│ │ 4          │ │ 86         │ │ 12         │ │  permitted)│                   │
│ └────────────┘ └────────────┘ └────────────┘ └────────────┘                   │
│                                                                               │
│ ┌─────────────────────────────┐  ┌──────────────────────────────────────────┐ │
│ │ PRODUCTION THIS WEEK        │  │ CHANNEL HEALTH                           │ │
│ │ Blog ██ Social ██ Email ██  │  │ Site · Ads · Social · Email              │ │
│ │ Source: marketing production│  │ Honest empty if channel not connected    │ │
│ │ Drill → Content Studio      │  │                                          │ │
│ └─────────────────────────────┘  └──────────────────────────────────────────┘ │
│                                                                               │
│ CAMPAIGNS (cards or simple list — not 12-step wizard on home)                 │
│  • Summer Launch — Active — 42 leads — [Open]                                 │
│  • Marina Awareness — Draft — [Continue]                                      │
│  [+ New campaign]  (wizard stays, launched from here)                         │
│                                                                               │
│ Advanced ▾ → Advertising, Attribution, Forecasting, Automations, Vendors, AI  │
│ (routes exist; hidden from default chrome)                                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## What leaves the default nav

WhatsApp, SMS, forecasting, attribution, vendor management, multi-AI pages, 9 dashboard sub-routes — accessible via Advanced or deep links, not primary chrome.
