# Changelog
<!-- markdownlint-disable no-duplicate-heading -->

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## [v1.6.2] - 2026-08-06

### Fixed

- Corrected Query DSL null/presence translation for Airtable so numeric `0` is treated as a set value (not blank).
- Replaced `BLANK()`-based presence checks with `COUNTA(...)`-based checks where appropriate.

### Changed

- Aligned value-presence semantics across operators:
  - `{"field": {"$exists": True}}` -> `COUNTA({field})!=0`
  - `{"field": {"$exists": False}}` -> `COUNTA({field})=0`
  - `{"field": {"$ne": None}}` -> `COUNTA({field})!=0`
  - `{"field": {"$eq": None}}` -> `COUNTA({field})=0`
- Added `None`-aware handling in list operators:
  - `$in` treats `None` entries as blank checks (`COUNTA({field})=0`)
  - `$nin` treats `None` entries as non-blank checks (`COUNTA({field})!=0`)

### Tests

- Updated functional query-to-formula matrix coverage for:
  - `$eq: None`
  - `$ne: None`
  - `$exists: true/false`
  - `$in`/`$nin` containing `None`
- Added integration coverage validating blank-vs-zero behavior against Airtable API for:
  - `$ne: None`
  - `$eq: None`
  - `$exists: true`
  - `$exists: false`
  - `$in` with `None`
  - `$nin` with `None`

## [v1.6.1] - 2026-07-30

### Changed

- Bumped `aracnid-core` dependency from `1.5.0` to `1.5.1`.

### Core Query DSL Semantics (via `aracnid-core` v1.5.1)

- Empty predicate `{}` is now accepted as logical TRUE when used under `$and` / `$or`.
- Logical identity normalization is now applied, including:
  - `{"$and": [{}, P]}` -> `P`
  - `{"$and": [{}, {}]}` -> `{}`
  - `{"$or": [P, {}]}` -> `{}`
- Strict invalid cases are unchanged:
  - `{"$not": {}}` remains invalid
  - empty field operator objects like `{"field": {}}` remain invalid
- Query DSL documentation and core contract tests were updated to reflect this behavior.

### Compatibility

- No connector API changes in this package; behavior updates come from shared core semantics in `aracnid-core`.

## [v1.6.0] - 2026-07-26

### Added

- Added Query DSL `$regex` support in `read_many()` formula translation.
- Added support for regex `$options` in Query DSL (currently `i` for case-insensitive matching).

### Validation & Errors

- Added connector-level regex guardrails for untrusted query inputs:
  - invalid regex patterns are rejected with clear runtime errors,
  - non-string-field regex usage is rejected when Airtable field metadata is available,
  - regex options are explicitly validated (only `i` is supported),
  - max regex pattern length policy is enforced,
  - regex meta-token complexity policy is enforced.

### Tests

- Added functional converter coverage for:
  - `$regex` pattern translation to `REGEX_MATCH(...)`
  - `$regex` + `$options: "i"` case-insensitive translation
  - invalid regex pattern rejection
  - non-string field regex rejection
  - unsupported `$options` rejection
  - excessive pattern length rejection
  - excessive pattern complexity rejection
- Added integration coverage to verify:
  - anchored prefix regex matching
  - case-insensitive regex matching with `$options: "i"`

## [v1.5.0] - 2026-07-25

### Added

- Added `delete_many(query, hard=False) -> int` to `AirtableConnector`.
  - Supports query-driven bulk deletion of Airtable records.
  - Returns the number of records deleted as an integer count.

### Behavior

- `delete_many` resolves matching records from `query`, then performs batch deletion via Airtable.
- If no records match, `delete_many` returns `0`.
- Soft delete is not supported for Airtable:
  - calling `delete_many(..., hard=False)` raises a runtime error (consistent with `delete_one` behavior).

### Validation & Errors

- Input validation added for:
  - `query` must be a `dict`
  - `hard` must be a `bool`
- Backend failures are wrapped using connector-standard runtime error handling.

### Tests

- Added functional tests for:
  - soft-delete rejection
  - no-match return value
  - query-to-batch-delete flow
  - backend exception wrapping
- Added integration tests for:
  - deleting all matching records
  - preserving non-matching records
  - no-match behavior
  - soft-delete rejection

## [v1.4.0] - 2026-07-25

### Added

- Added `update_many(query, changes) -> int` to `AirtableConnector`.
  - Supports query-driven bulk partial updates.
  - Applies `changes` to all records matching `query`.
  - Returns the number of updated records as an `int`.

### Changed

- Bulk updates now use Airtable batch update semantics internally (`pyairtable.batch_update` payload format).
- `update_many` reuses existing write normalization logic for outbound field values.

### Validation & Errors

- `update_many` validates inputs:
  - `query` must be a `dict`
  - `changes` must be a non-empty `dict`
- Connector-standard runtime error wrapping is applied for backend failures.

### Notes

- This release establishes count-based return semantics for bulk updates in `aracnid-airtable` (`int` affected rows).

## [v1.3.6] - 2026-07-24

### Changed

- Added Airtable `currency` field read coercion to Python `Decimal`.
- Added write normalization for Python `Decimal` values when writing to Airtable:
  - Quantizes to 2 decimal places using `_CURRENCY_QUANT = Decimal("0.01")`.
  - Converts quantized value to numeric Airtable-compatible input.
- Kept existing non-currency coercion behavior unchanged while extending currency-specific handling.

### Tests

- Added integration coverage to verify currency read coercion returns `Decimal`.
- Added round-trip integration coverage for creating records with `Decimal` currency values and reading them back as `Decimal`.

### Notes

- Currency fields now return `Decimal` instead of `float` on reads.
- This is a backward-compatible patch for connector behavior, but consumers with strict float expectations should update type assertions accordingly.

## [v1.3.5] - 2026-07-24

### Changed

- Coerced Airtable record `createdTime` into Python `datetime` during read normalization (`_created_time`).
- Added coercion support for Airtable `last_modified_time` fields to Python `datetime`.

### Tests

- Updated functional tests to expect `_created_time` as a `datetime` (UTC-aware) instead of a raw string.
- Added/updated integration coverage to verify coercion of:
  - `_created_time` (from Airtable `createdTime`)
  - last-modified datetime fields (e.g., `Updated` / `last_modified_time`)

### Notes

- Consumers previously treating `_created_time` as a string should now use datetime handling (or call `.isoformat()` if string output is needed).

## [v1.3.4] - 2026-07-23

### Changed

- Upgraded `pyairtable` to **v3.4.0**.
- Updated Airtable field type handling to align with `pyairtable` v3.4.0 schema/type representations.
- Normalized field type name handling across connector coercion paths to support updated type value formats consistently.

### Tests

- Updated field type/coercion tests to reflect `pyairtable` v3.4.0 field type naming.
- Refreshed related date/datetime and formula-field coercion assertions to match the new normalized type behavior.

### Notes

- This release is focused on dependency alignment and compatibility with `pyairtable` v3.4.0.
- No intended changes to external connector API behavior beyond field type representation compatibility.

## [v1.3.3] - 2026-07-23

### Fixed

- Improved Airtable **formula field** read coercion for date/time values.
- Added handling for Airtable schema ambiguity where formula outputs that represent datetimes may appear as date-typed in metadata.
- Formula date-like outputs now use datetime-shape detection to route values through existing datetime coercion when appropriate.

### Changed

- Read normalization remains schema-first, with a targeted fallback for ambiguous formula date/datetime outputs.
- Existing non-formula `date` / `dateTime` coercion behavior is unchanged.

### Compatibility

- Backward compatible patch release.
- No timezone policy changes; formula datetime coercion reuses existing connector/core timezone handling.

## [v1.3.2] - 2026-07-22

### Added

- Added schema-aware read coercion for Airtable field types:
  - `date` → `datetime.date`
  - `dateTime` → timezone-aware `datetime.datetime`
- Added shared contract test shims to run `aracnid-core` datetime/timezone contract coverage:
  - `tests/contract/test_datetime_tz_contract.py`
  - `tests/contract/test_timezone_env_contract.py`

### Changed

- Integrated `aracnid-core` timezone handling for Airtable `dateTime` coercion:
  - `ARACNID_DATETIME_TZ_MODE=utc|local|keep`
  - `ARACNID_LOCAL_TIMEZONE=<IANA timezone>` (required when mode is `local`)
- Datetime coercion now follows shared core behavior:
  - `utc` (default) normalizes aware datetimes to UTC
  - `local` normalizes to explicitly configured IANA timezone
  - `keep` preserves source timezone/offset
- Record normalization now applies coercion based on Airtable schema metadata via cached field-type mapping.

### Validation

- Invalid datetime/date strings continue to pass through unchanged.
- Naive datetimes are rejected per shared core validation rules.
- `ARACNID_DATETIME_TZ_MODE=local` without `ARACNID_LOCAL_TIMEZONE` fails fast with `ValueError`.

### Compatibility

- Backward compatible for consumers treating values generically.
- Consumers that assumed Date/DateTime values were always strings should update expectations to Python-native date/datetime types.

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
