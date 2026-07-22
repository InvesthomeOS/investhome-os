# Frontend UI Dependency Audit — D1B.5

**Product:** INVESTHOME OS  
**Scope:** Root / `apps/web` / `packages/ui` manifests, `pnpm-lock.yaml`, CSS stack, UI-related imports  
**Date:** 2026-07-20  
**Lockfile:** `pnpm-lock.yaml` (pnpm 9.15.0)

---

## Verdict

Lean, custom Design System–first stack. **No Tailwind, Radix, Headless UI, Chart.js/Recharts, Lucide, cmdk, sonner, framer-motion, or dnd libraries.** Charts and icons are first-party SVG. One heavy visualization dependency: `react-force-graph-2d` (CRM relationships only).

---

## Package manifests

### Root `package.json`

No UI runtime deps. Tooling: `turbo`, `typescript`, `prettier`, `rimraf`, `@types/node`.

### `packages/ui/package.json`

| Item | Value |
|------|-------|
| Name | `@investhome/ui` `0.1.0` |
| Runtime deps | none |
| Peers | `react` / `react-dom` `^19.0.0` |
| Role | DS components + `designTokens` / `brandTokens` / `motionTokens` |

### `apps/web/package.json` — UI-relevant runtime

| Package | Specifier | Lock resolved |
|---------|-----------|---------------|
| `next` | `^15.1.0` | **15.5.20** |
| `react` / `react-dom` | `^19.0.0` | **19.2.7** |
| `@investhome/ui` | `workspace:*` | link |
| `@investhome/shared` | `workspace:*` | link |
| `next-intl` | `^4.13.2` | **4.13.2** |
| `@tanstack/react-query` | `^5.62.8` | **5.101.2** |
| `zustand` | `^5.0.2` | **5.0.14** |
| `react-hook-form` | `^7.81.0` | **7.81.0** |
| `@hookform/resolvers` | `^5.4.0` | **5.4.0** |
| `zod` | `^4.4.3` | **4.4.3** |
| `react-force-graph-2d` | `^1.29.1` | **1.29.1** |

---

## CSS / styling architecture

| Item | Status |
|------|--------|
| Tailwind / PostCSS / Autoprefixer | **Not present** |
| CSS frameworks (Bootstrap, MUI, Chakra) | **Not present** |
| CSS-in-JS as DS | **Not used** |
| Token CSS | `apps/web/src/app/theme-tokens.css` |
| Global CSS | `apps/web/src/app/globals.css` |
| DS CSS | `apps/web/src/app/design-system.css` |
| Motion | `apps/web/src/app/motion-system.css` + `packages/ui/src/motion-tokens.ts` |
| Component CSS | `ih-components.css`, workspace themes, feature CSS |

**Model:** hand-authored CSS + semantic CSS variables + `@investhome/ui` classnames (`ds-*`, `ih-*`).

---

## Inventory (per package)

### `@investhome/ui` — `0.1.0` (workspace)

| Field | Value |
|-------|-------|
| Purpose | Shared DS primitives, tokens |
| Where used | Widespread under `apps/web/src` (admin, company, CRM, marketing, analytics, design-system, sales, …) |
| Active | yes |
| Duplicated | partial — local modal wrappers alongside `Dialog` |
| DS v1 compatible | yes |
| Recommendation | **keep** — expand as single component source |
| Migration risk | n/a |
| Bundle concern | low |

### `next` — 15.5.20

| Field | Value |
|-------|-------|
| Purpose | App framework, routing, SSR |
| Where used | Entire `apps/web` |
| Active | yes |
| Duplicated | no |
| DS v1 compatible | yes |
| Recommendation | **keep** |
| Migration risk | low |
| Bundle concern | medium (framework baseline) |

### `react` / `react-dom` — 19.2.7

| Field | Value |
|-------|-------|
| Purpose | UI runtime |
| Active | yes |
| DS v1 compatible | yes |
| Recommendation | **keep** |
| Migration risk | low |
| Bundle concern | medium |

### `next-intl` — 4.13.2

| Field | Value |
|-------|-------|
| Purpose | i18n (TR primary, EN secondary) |
| Where used | App layout, pages, showcase (`designSystem.*`) |
| Active | yes |
| Duplicated | no |
| DS v1 compatible | yes |
| Recommendation | **keep** |
| Migration risk | low |
| Bundle concern | low–medium |

### `@tanstack/react-query` — 5.101.2

| Field | Value |
|-------|-------|
| Purpose | Server/async state for workspaces |
| Where used | CRM/marketing/company workspaces; `lib/query/query-provider.tsx` |
| Active | yes |
| Duplicated | no (Zustand = local UI state) |
| DS v1 compatible | yes |
| Recommendation | **keep** |
| Migration risk | low |
| Bundle concern | low |

### `zustand` — 5.0.14

| Field | Value |
|-------|-------|
| Purpose | Client UI/workspace stores |
| Where used | CRM/marketing/company stores |
| Active | yes |
| Duplicated | no |
| DS v1 compatible | yes |
| Recommendation | **keep** |
| Migration risk | low |
| Bundle concern | low |

### `react-hook-form` — 7.81.0 + `@hookform/resolvers` — 5.4.0

| Field | Value |
|-------|-------|
| Purpose | Form state + Zod resolvers |
| Where used | CRM communication/forms (signatures, sequences, calls, templates, composer, company form) |
| Active | yes (CRM-focused; many forms still use `useState`) |
| Duplicated | partial — mixed form patterns |
| DS v1 compatible | yes |
| Recommendation | **keep**; consolidate onto RHF+Zod over time |
| Migration risk | medium |
| Bundle concern | low |

### `zod` — 4.4.3

| Field | Value |
|-------|-------|
| Purpose | Schema validation |
| Where used | CRM/marketing schemas |
| Active | yes |
| Duplicated | no |
| DS v1 compatible | yes |
| Recommendation | **keep** |
| Migration risk | low |
| Bundle concern | low |

### `react-force-graph-2d` — 1.29.1

| Field | Value |
|-------|-------|
| Purpose | Interactive 2D force-directed relationship graph |
| Where used | Only `apps/web/src/app/workspaces/crm/relationships/_components/relationship-network-view.tsx` (dynamic import, `ssr: false`) |
| Active | yes |
| Duplicated | no |
| DS v1 compatible | partial (canvas overlay; not token-driven charts) |
| Recommendation | **keep** if CRM network stays; else **remove later** |
| Migration risk | medium |
| Bundle concern | **high** |

**Transitive (via `force-graph@1.51.4`):** `d3-array`, `d3-drag`, `d3-force-3d`, `d3-scale`, `d3-scale-chromatic`, `d3-selection`, `d3-zoom`, `float-tooltip`, `@tweenjs/tween.js`, etc. Treat as graph internals — **not** an app chart stack.

---

## First-party UI systems (not npm)

| System | Location | Purpose | Active | Duplicated | DS v1 | Recommendation | Risk | Bundle |
|--------|----------|---------|--------|------------|-------|----------------|------|--------|
| Custom SVG charts | `apps/web/src/components/design-system/charts/*` | Line/Area/Bar/Donut/… | yes | no | yes | keep | low | low |
| `ChartContainer` | `packages/ui` | Chart chrome/states | yes | no | yes | keep | low | low |
| `IhIcon` | `apps/web/src/components/icons/ih-icons.tsx` | Inline SVG icons | yes | no | yes | keep | low | low |
| CSS motion | `motion-system.css` | Transitions | yes | no | yes | keep | low | none |
| `Dialog` / `Drawer` | `packages/ui` | Modal / panel | yes | partial vs local modals | yes | keep; migrate wrappers | medium | low |
| Toast stacks | admin/company/investor hooks | Notifications | yes | **yes** (in-house) | yes | consolidate later | medium | low |
| Global search palette | `global-search-palette.tsx` | Command-palette UX | yes | no (not cmdk) | yes | keep | low | low |
| Native date inputs | `DateRangeControl` + `type="date"` | Date range | yes | no | yes | keep | low | none |

---

## Explicitly NOT present

| Category | Missing |
|----------|---------|
| CSS utility | Tailwind, PostCSS, Sass |
| Component kits | `@radix-ui/*`, Headless UI, MUI, Chakra, Ant, Bootstrap, shadcn |
| Charts (direct) | recharts, chart.js, victory, @nivo/*, visx |
| Icons | lucide-react, heroicons, react-icons |
| Toasts | sonner, react-hot-toast |
| Command menu | cmdk |
| Motion JS | framer-motion |
| DnD | @dnd-kit, react-beautiful-dnd |
| Dates | date-fns, dayjs, moment, react-day-picker |
| Tables | @tanstack/react-table, ag-grid |
| Editors | tiptap, slate, lexical |
| Selects | react-select |
| Class helpers | clsx, classnames, cva |

---

## Recommendations

1. **Keep** custom CSS tokens + `@investhome/ui` as DS v1 backbone — do not introduce Tailwind/Radix without a platform decision.
2. **Keep** `react-force-graph-2d` only for CRM network (already dynamically imported).
3. **Consolidate** toast APIs into one DS primitive before adding external toast libs.
4. **Consolidate** form modals onto `Dialog` + RHF+Zod where validation matters.
5. **Do not add** Recharts/Chart.js unless custom SVG charts hit a capability wall.
6. **Investigate later:** move `IhIcon` into `@investhome/ui` for package boundary clarity.

---

*Related:* [component-source-of-truth.md](./component-source-of-truth.md) · [ui-migration-plan.md](./ui-migration-plan.md)
