# 13 — Fields to Hide (Progressive Disclosure)

Hide behind **Details**, **Advanced**, accordion, or role-gated tabs. Do not delete from API/schema.

---

## Customers / Leads

| Field group | Examples |
|-------------|----------|
| Geography | Country, city, full address |
| Attribution deep | UTM source/medium/campaign, campaign id |
| Qualification deep | Score breakdown, checklist internals |
| Budget precision | Exact estimated_budget (show band first) |
| Comms handles | LinkedIn, secondary phones/emails, WhatsApp id |
| Compliance | KYC flags, accreditation (show when Investor role) |

---

## Investor path (on Customer)

| Field group | Examples |
|-------------|----------|
| Investment prefs | Preferred model, min/max ticket, capacity, markets, risk profile |
| Accreditation | accreditation_status |
| History dates | last_contact, next_follow_up duplicates if already in header |

---

## Inventory unit

| Field group | Examples |
|-------------|----------|
| Legal | legal_identifier |
| Spatial detail | Orientation, view, exterior area split, unit_subtype |
| Dates | Release date, delivery date |
| Secondary statuses | Construction, closing, leasing (unless role needs them) |
| Long text | Description, internal notes |

---

## Projects (create + Advanced tab)

| Field group | Examples |
|-------------|----------|
| Geo | Lat/long, timezone, full address block |
| Ownership / legal | Ownership type, development_type deep enums |
| Unit planning counts | Full sqft breakdowns on create |
| Financial projections (~15) | Acquisition, budgets, ROI/IRR, equity, debt — Finance tab |
| Dense construction | Permits, cost lines — advanced/construction roles |

---

## Marketing / Content

| Field group | Examples |
|-------------|----------|
| SEO / UTM on content | Details drawer |
| Approval workflow config | Advanced |
| Vendor / budget / attribution models | Marketing Advanced |
| AI prompt settings | AI restricted area |

---

## Principle

**Create flows:** 5–8 fields max.  
**Edit flows:** show daily fields; Advanced collapsed.  
**Never** dump investor + lead + UTM + compliance on one modal.
