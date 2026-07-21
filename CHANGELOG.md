# Changelog
<!-- markdownlint-disable no-duplicate-heading -->

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## [v1.3.0] - 2026-07-21

### Added

- Added Query DSL `sort` support to `read_many(...)` in the Airtable connector.
- Added Mongo-style sort input support via core DSL shape:
  - `sort=[{"FieldA": 1}, {"FieldB": -1}]`
- Added Airtable sort translation helper for pyairtable-compatible ordering.

### Changed

- Updated normalized adapter read path to accept both:
  - `query_dsl`
  - `sort_dsl`
- Mapped normalized sort DSL to pyairtable sort format:
  - ascending: `"FieldName"`
  - descending: `"-FieldName"`
- Preserved sort precedence order across multi-field sorts.
- Standardized no-sort handling to an empty sort list (`[]`) in adapter flow.

### Tests

- Expanded functional tests for sort translation and `read_many(..., sort=...)` behavior.
- Expanded integration tests for:
  - single-field sorting
  - multi-key precedence
  - combined query + sort behavior

## [v1.2.0] - 2026-07-19

### Changed

- Integrated `aracnid-core` v1.2.0 temporal semantics into the Airtable connector.
- Updated Airtable write paths (`create_one`, `update_one`, `replace_one`) to normalize aware `datetime` values to Airtable-safe UTC ISO-8601 (`...Z`) literals.
- Added strict write-path validation for temporal inputs:
  - naive `datetime` values are rejected with `ValueError`,
  - `date` values are normalized as ISO calendar dates (`YYYY-MM-DD`).

### Contract / Conformance

- Extended contract conformance re-exports to include Query DSL temporal semantics tests:
  - accepts timezone-aware local datetimes,
  - accepts timezone-aware UTC datetimes,
  - rejects naive datetimes,
  - accepts `date` literals.

### Integration Tests

- Added integration coverage for temporal behavior end-to-end with Airtable:
  - naive datetime rejection symmetry across `create_one` / `update_one` / `replace_one`,
  - date write round-trip behavior across `create_one` / `update_one` / `replace_one`,
  - Query DSL date equality with Python `date` literals,
  - DST-focused instant-equivalence checks (local aware datetime vs equivalent UTC instant).

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
