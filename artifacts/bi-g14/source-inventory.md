# G14 Source Inventory

| Domain | OLTP sources (SSOT) | Warehouse targets | Ingestion |
|--------|---------------------|-------------------|-----------|
| Finance / cash | `financial_accounts`, `finance_transactions`, `payment_obligations` | `wh_fact_cash_movement`, mart cash | incremental + full |
| Sales / pipeline | `sales_opportunities` | `wh_fact_pipeline` | daily snapshot |
| Investors | `investors` | `wh_dim_investor`, `wh_fact_investor_activity` | SCD1 + daily snap |
| Projects | `projects` | `wh_dim_project`, status history | SCD1 + events |
| Marketing | `marketing_campaigns` (+ budget_amount proxy) | `wh_dim_campaign`, `wh_fact_marketing_spend` | upsert |
| Time / FX | — | `wh_dim_date`, `wh_dim_currency`, `wh_fx_rates` | seed + identity FX |
| Metrics | P9 `analytics_metric_registry` | `wh_metric_catalog` | sync on ingest |
| Governance | — | `wh_governed_datasets`, `wh_lineage_edges`, `wh_dq_check_results`, `wh_export_audit`, `wh_scheduled_reports` | sync / admin |

**Not in certified set (draft / blocked):** website connector metrics, full forecast/ML accuracy, Metabase hybrid, dbt Core.
