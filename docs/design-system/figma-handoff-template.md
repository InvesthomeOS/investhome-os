# Figma Handoff Template — D1B.5

**Product:** INVESTHOME OS  
**Locales:** Turkish primary, English secondary  
**Code mirrors:** [figma-component-map.md](./figma-component-map.md) · [figma-variables-spec.md](./figma-variables-spec.md) · `packages/ui/src/design-asset-registry.ts`

Use this checklist when handing a **screen** or **component** from Figma to engineering.

---

## A. Screen handoff checklist

### Identity

- [ ] Product name shown as **INVESTHOME OS** (not InvestorOS / Investom)
- [ ] Screen maps to an **existing route** from [navigation-map.md](./navigation-map.md) — no invented Portfolio / Properties / Deals
- [ ] Permission / role assumptions documented (who can see this?)
- [ ] Locale frames: TR default; EN parity for new copy

### Layout

- [ ] Breakpoints annotated: **1100** (DS desktop), **768** (tablet), **≤767** (mobile), **960** (shell collapse) — see [responsive-component-contract.md](./responsive-component-contract.md)
- [ ] Dashboard grid spans only **3 / 4 / 6 / 8 / 12**
- [ ] Widgets are **independent surfaces** (no merged multi-chart canvas)
- [ ] Information hierarchy respected when applicable (alerts → KPIs → trends → …)

### Tokens

- [ ] Colors/spacing/type/radius/shadow use **Figma Variables** from [figma-variables-spec.md](./figma-variables-spec.md)
- [ ] No designer-facing gray-200 / blue-500 ramps
- [ ] Status colors only for meaning

### Components

- [ ] Each instance linked to a library component named `Category / Family / Variant / Size`
- [ ] Variants match [component-variant-contract.md](./component-variant-contract.md)
- [ ] Missing code variants listed explicitly (do not silently invent)
- [ ] Icons from **IhIcon** catalog only ([icon-system.md](./icon-system.md))

### Charts & tables

- [ ] Chart type + height token (compact / standard / large / hero)
- [ ] Chart palette from Chart variables
- [ ] Table density: compact / standard / comfortable
- [ ] Tables vs cards decision noted

### Content & a11y

- [ ] Empty / loading / error states designed
- [ ] Icon-only controls have labels
- [ ] Focus order / modal behavior noted for overlays
- [ ] Demo data labeled **demo only** if not production-ready

### Engineering packet

- [ ] Link to Figma frame + component keys
- [ ] Registry `figmaName` targets listed for new primitives
- [ ] Out of scope called out (API/DB/business logic unchanged)
- [ ] Wave assignment (1–5) from [ui-migration-plan.md](./ui-migration-plan.md)

---

## B. Component handoff checklist

### Identity

- [ ] Figma name: `Category / Family / Variant / Size`
- [ ] Code name + import path (from map or proposed)
- [ ] Owner: `packages/ui` | `apps/web design-system` | domain
- [ ] Classification: Canonical / Domain-specific / Experimental / …

### API

- [ ] Property table: Figma prop → code prop → values
- [ ] States: default / hover / focus / disabled / loading / error / empty as applicable
- [ ] Sizes / densities / spans documented
- [ ] Responsive notes (real breakpoints only)

### Quality

- [ ] a11y: roles, labels, focus, contrast
- [ ] i18n: caller-owned strings vs built-in defaults
- [ ] Tokens only (no raw hex in new components)
- [ ] No new npm UI dependency without audit update

### Delivery

- [ ] Added/updated row in [figma-component-map.md](./figma-component-map.md)
- [ ] Added/updated entry in `design-asset-registry.ts`
- [ ] Showcase section updated if Canonical (admin-only)
- [ ] Tests for registry validity if metadata added

---

## C. Copy-paste brief (short form)

```
Screen / Component:
Route (existing):
Permissions:
Wave (1–5):
Figma link:
Variables used:
Components (Figma → code):
Breakpoints annotated: 1100 / 768 / 767 / 960
States: ready / loading / empty / error
i18n: TR + EN
Out of scope:
Risks:
```

---

*End of handoff template.*
