# Pipeline

MOEX historical market-data infrastructure.

## Scope

1. Historical securities universe discovery and classification.
2. Full-history raw daily bar collection from MOEX ISS.
3. Data-quality audits and collection coverage reports.
4. Separate downstream transformation and panel-building stages.

Raw source data and generated datasets are local-only and must not be committed.

## Local layout

```text
pipeline/
├── data/                 # local data only (gitignored)
├── scripts/
│   ├── dataset/          # dataset collection/build steps
│   └── tools/            # orchestration and utilities
└── docs/
```

## Collection principles

- Preserve raw MOEX observations; do not silently repair or delete them.
- Record source security and board identifiers.
- Download tasks must be resumable and idempotent.
- Keep collection, transformation, and panel construction separate.
- Persist failures and progress for auditability.
- Never commit raw databases, parquet files, or API caches.

## Status

Repository bootstrap. Historical raw download implementation is being staged.