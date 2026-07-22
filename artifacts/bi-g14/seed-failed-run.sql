INSERT INTO analytics.wh_ingestion_runs (
  id, domain, job_name, mode, status,
  rows_read, rows_written, rows_rejected,
  reject_reasons_json, error_message,
  started_at, finished_at, created_at
) VALUES (
  gen_random_uuid(),
  'warehouse',
  'warehouse_ingestion_incremental',
  'incremental',
  'failed',
  10, 0, 10,
  '["demo_forced_failure"]'::json,
  'Forced failed state for G14 screenshot evidence',
  now() - interval '5 minutes',
  now() - interval '4 minutes',
  now()
);
