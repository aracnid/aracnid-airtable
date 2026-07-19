# Changelog
<!-- markdownlint-disable no-duplicate-heading -->

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-07-19

### Added

- Implemented Query DSL support for `read_many()` in the Airtable connector.
- Added support for core query patterns and operators used in application queries, including:
  - field equality (shorthand and `$eq`)
  - `$ne`
  - `$exists` (`true` / `false`)
  - `$contains`
  - logical `$and` composition
- Expanded integration test coverage for Query DSL behavior across:
  - logical/operator combinations
  - numeric literal equivalency (`int`, `float`)
  - date/datetime matching scenarios
  - string quoting/escaping edge cases (quotes, backslashes, whitespace, newlines, unicode)

### Changed

- Improved formula/literal translation for Query DSL-driven `read_many()` queries to produce valid Airtable formulas across supported operators and literal types.

### Fixed

- Fixed query formula composition issues that could produce invalid Airtable formula expressions in nested/combined Query DSL filters.
- Added integration test teardown cleanup so seeded records are deleted after test runs, preventing leftover Airtable test data.

## [1.0.3] - 2026-07-15

### Added

- Preflight checklist

### Changed

- Migrated package metadata to `[project]` in `pyproject.toml`.
- Added `dynamic = ["dependencies"]` to align Poetry + PEP 621.
- Updated Ruff target to Python 3.12

## [1.0.0] - 2026-07-15

### Added

- Rename project from `i-airtable` to `aracnid-airtable`.
- Functional unit tests for `AirtableConnector` covering:
  - Record normalization behavior.
  - Create/read/update/replace/delete behavior with mocked Airtable table methods.
  - Not-found and backend exception handling paths.
- Integration tests for real Airtable behavior, including:
  - CRUD round-trip scenarios.
  - Filtered reads.
  - Not-found semantics.
  - Hard-delete-only behavior.
- Pytest marker configuration for integration test selection.

### Changed

- Test organization now clearly separates local/fast tests from external-service integration tests.
- Fixture/type annotations in tests were refined to satisfy static analysis (generator fixture typing, mock usage clarity).
- Functional test expectations were adjusted to accept Airtable formula objects (not only raw strings).

### Fixed

- Type mismatch around normalization input typing (`RecordDict` vs `dict[str, Any]`) in connector/test usage.
- Lint/type-check issues in integration fixtures and mock-based functional tests.

## [0.1.0] - 2025-05-18

### Added

- Initial project scaffolding and package setup.
- Initial Airtable connector implementation.
- Packaging and publishing workflow to PyPI.
- Basic project metadata and dependency configuration.

---

[1.0.3]: https://github.com/aracnid/aracnid-airtable/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/aracnid/aracnid-airtable/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/aracnid/aracnid-airtable/releases/tag/v0.1.0
