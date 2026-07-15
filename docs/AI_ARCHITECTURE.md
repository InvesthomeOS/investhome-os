# AI Architecture

## Providers (current)

| Capability | Default | Config |
|------------|---------|--------|
| Text analysis / Q&A | Local heuristic | `AI_PROVIDER`, `AI_MODEL` |
| OCR | Local | `OCR_PROVIDER` |
| External LLM | Not connected | `AI_API_KEY` (optional) |

## Pipeline

```
Document upload → process_document_job (ARQ or sync)
    → extraction → chunking → classification → optional Q&A
Drawing upload → process_drawing_job
    → detection → sheet/element analysis
```

## Confidentiality policy

Environment flags (not feature flags):

- `AI_ALLOW_EXTERNAL_FOR_CONFIDENTIAL=false`
- `AI_ALLOW_EXTERNAL_FOR_HIGHLY_CONFIDENTIAL=false`

Company Foundation preferences mirror these (`ai.allow_external_confidential`).

## Data storage

- **Chunks** in `document_chunks` table
- **Conversations** in `document_conversations` / `document_messages`
- **Usage** tracked in `ai_usage`

## Honest degradation

Local providers return deterministic/heuristic results. UI must not claim external AI is connected unless `/settings/providers` reports `configured: true`.

## Future integration

1. Provider adapter interface in `services/document_intelligence/ai.py`
2. Secret references via env only
3. Feature flag `FEATURE_EXTERNAL_AI` gates runtime calls
4. Activity log + AI usage for audit

See [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md).
