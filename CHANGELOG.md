# Changelog

## [1.1.0] - 2026-04-06

### Added
- `PRIVATE_JOURNAL_PATH` environment variable to override all journal storage to a single directory, for containerized deployments (#8 related)
- 30-second timeout on embedding model initialization to prevent server hangs from stale lock files (#5)

### Fixed
- Migrated from CommonJS to ESM output, fixing `tools/list` returning empty on Node.js 22+ due to CJS/ESM dual-package hazard (#18)
- Fixed test expectations for embedding file generation (file count and semantic search assertions)

### Changed
- `jest.config.js` renamed to `jest.config.cjs` (required by ESM migration)
- TypeScript target updated from ES2020 to ES2022 with NodeNext module resolution

## [1.0.0] - 2025-05-28

Initial release with multi-section journaling, semantic search, and dual project/user storage.
