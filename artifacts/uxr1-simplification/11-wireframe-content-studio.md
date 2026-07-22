# 11 — Wireframe: Content Studio

**Fidelity:** Low · **Route:** `/dashboard/marketing/content`  
**Consolidates:** blog/long-form, social, email drafts, templates, assets library entry

---

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Marketing / Content Studio                                                    │
│ [ All ] [ Blog ] [ Social ] [ Email ] [ Templates ] [ Assets ]                │
│                          [Search]  [Filter status]  [+ Create ▾]              │
│ Create ▾ → Blog post · Social post · Email · From template                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│ │ Draft        │ │ Scheduled    │ │ Published    │ │ Needs approve│           │
│ │ Marina guide │ │ Summer reel  │ │ ROI tips     │ │ Email #12    │           │
│ │ Blog · Selim │ │ Social·Ayşe  │ │ Blog · …     │ │ Email · …    │           │
│ │ Updated 2h   │ │ Thu 10:00    │ │ 18 Jul       │ │ Waiting      │           │
│ └──────────────┐ └──────────────┘ └──────────────┘ └──────────────┘           │
│                                                                               │
│ List/table toggle available for bulk ops; cards default.                      │
│                                                                               │
│ EDITOR (create/edit)                                                          │
│ ┌────────────────────────────────────────────┬──────────────────────────────┐ │
│ │ Title                                      │ Status: Draft                │ │
│ │ Body / blocks                              │ Channel: Blog                │ │
│ │                                            │ Campaign: Summer Launch      │ │
│ │                                            │ Schedule                     │ │
│ │                                            │ Approvals                    │ │
│ │                                            │ SEO / UTM (Details ▸)        │ │
│ │                                            │ [Save] [Submit] [Publish]    │ │
│ └────────────────────────────────────────────┴──────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Creation map (target)

| Content | Create in Content Studio | Notes |
|---------|--------------------------|-------|
| Blog / insights | Yes | Publishes toward `(site)/insights` |
| Social posts | Yes (Social tab) | Former `/workspaces/marketing/social` |
| Email | Yes (Email tab) | Former email campaign new |
| Templates | Yes | Shared |
| Assets | Tab / library link | Media |
| Landing pages / forms | Advanced under Marketing | Not default Content Studio clutter |
| Design Studio furniture | **Not here** | Separate product design tool |

---

## Empty states

- No drafts: “Create your first piece — blog, social, or email.”
- Channel disconnected: honest banner, no fake engagement charts.
