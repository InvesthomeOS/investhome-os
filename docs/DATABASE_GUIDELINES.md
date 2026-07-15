# Investhome OS — Database Guidelines

**Last updated:** 2026-07-15

PostgreSQL conventions for SQLAlchemy models and Alembic migrations.

**Related:** [NAMING_CONVENTIONS.md](./NAMING_CONVENTIONS.md) · [VERSIONING_POLICY.md](./VERSIONING_POLICY.md) · [DATA_OWNERSHIP.md](./DATA_OWNERSHIP.md) · [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) (IAD-004, IAD-005, IAD-015)

---

## UUID Primary Keys

```python
id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
```

- All business entities use UUID PKs
- Foreign keys: `Uuid` type — `{entity}_id`
- No auto-increment integers for domain tables
- API exposes as string UUID in JSON

---

## Soft Delete & Archive

| Pattern | Usage |
|---------|--------|
| `archived_at` | Preferred soft-delete — nullable `DateTime(timezone=True)` |
| `archive` permission | Distinct from `delete` |
| Default queries | Filter `archived_at IS NULL` |
| Restore | Clear `archived_at` + activity `RESTORED` |
| Hard delete | Rare — admin only where implemented |

**Do not** use `is_deleted` boolean without timestamp — prefer `archived_at` for audit queries.

---

## History Tables

| Domain | History approach |
|--------|------------------|
| Documents | `document_versions` — explicit version rows |
| Activity | Append-only `activity_logs` — field diffs in JSON |
| Unit prices (planned) | `unit_prices` append-only |
| Unit status (planned) | `unit_status_history` |
| Finance | Activity log for field changes — no separate history table |

**Rule:** Financial and pricing changes must be auditable — either history table or activity `changed_fields`.

---

## Indexes

| Guideline | Example |
|-----------|---------|
| FK columns | Index foreign keys used in joins/filters |
| Unique business keys | `project_code`, `company_code` — `unique=True` |
| List filters | Index status, `archived_at`, `created_at` where queried |
| Search | PostgreSQL `ILIKE` / full-text — dedicated indexes per search provider |
| Composite | `(entity_type, entity_id)` on polymorphic links |

Add indexes in migration — not ad-hoc in production.

---

## Decimal / Money

```python
Mapped[Decimal] = mapped_column(Numeric(16, 2), ...)
```

| Field type | Precision |
|------------|-----------|
| Money / amounts | `Numeric(16, 2)` — finance, budgets |
| Smaller estimates | `Numeric(14, 2)` — lead budget |
| Currency | Separate `currency` string column — default `USD` |
| Rates | **Not implemented** — no conversion (TD-14) |

**Never** use `float` for money. Serialize as string in activity JSON via `_serialize_value`.

---

## Dates & Timezones

| Type | Usage |
|------|--------|
| `DateTime(timezone=True)` | All timestamps — `created_at`, `updated_at`, `archived_at` |
| `Date` | Business dates — `effective_date`, `due_date` |
| Server default | `func.now()` for `created_at` |
| Python | Use `datetime` with UTC awareness in services |
| API | ISO 8601 strings |

---

## Relationships

| Pattern | Usage |
|---------|--------|
| FK | Explicit `ForeignKey("table.id")` |
| ORM | `relationship()` where needed — avoid N+1 in list endpoints |
| Polymorphic | `DocumentLink` — `entity_type` + `entity_id` |
| Cascade | Careful — prefer soft archive over CASCADE DELETE |
| Nullable FK | Document `project_id` optional |

### Multi-company readiness

`company_id` on offices, brands, departments — nullable/unenforced in single-company runtime.

---

## Enums

```python
class Foo(str, enum.Enum):
    BAR = "bar"

mapped_column(Enum(Foo, native_enum=False, length=50))
```

- `native_enum=False` — stores string values, portable with SQLite tests
- New values require migration + code deploy
- i18n for display — not DB enum labels

---

## Migrations (Alembic)

| Rule | Detail |
|------|--------|
| Chain | Linear — `0001` through `0013` |
| Naming | `00NN_{description}.py` |
| Single head | Verify `alembic heads` before merge |
| Data seed | `db/*_seed.py` — idempotent |
| Downgrade | Test in staging |
| Apply on deploy | `alembic upgrade head` — **required** for 0013+ |

Current head in source: `0013_company_foundation`.

---

## Demo Data

`is_demo: bool` on business records — filter in production views if needed. Seeds are idempotent.

---

## JSON Columns

`metadata_json`, `changed_fields`, `previous_values`, `new_values` — use for flexible audit payloads.

Sanitize before write (activity service). Do not store secrets.

---

## Testing Database

- pytest uses in-memory **SQLite** via `conftest.py`
- 133+ tests — rebuild API image when testing without volume mount
- SQLite limitations: test PostgreSQL-specific features separately if needed

---

## Anti-patterns

| Anti-pattern | Why |
|--------------|-----|
| Money as float | Rounding errors |
| Hard delete default | Loses audit trail |
| Missing timezone | Ambiguous timestamps |
| Integer PKs for domain | Breaks merge/distribution |
| Branching migration heads | Deploy conflicts |
| Business logic in migrations | Hard to test — use seed scripts |

---

*Migration status per environment: [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md).*
