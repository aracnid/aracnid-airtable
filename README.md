# aracnid-airtable

A Python Airtable connector implementation for the `aracnid-base` contract.

## Overview

`aracnid-airtable` provides an `AirtableConnector` implementation that follows the shared connector interface used across `i-*` connector modules. It wraps Airtable CRUD operations with consistent validation, normalization, and error handling semantics.

## Installation

Using Poetry:

```bash
poetry add aracnid-airtable
```

Using pip:

```bash
pip install aracnid-airtable
```

## Requirements

- Python 3.12+
- Airtable API key with access to the target base/table

## Configuration

Set your Airtable API key in the environment:

```bash
export AIRTABLE_API_KEY=your_api_key
```

## Quick Start

```python
from aracnid_airtable.connector import AirtableConnector

connector = AirtableConnector(
    base_id="appXXXXXXXXXXXXXX",
    table_name="MyTable",
)

created = connector.create_one({"name": "example", "status": "active"})
record_id = created["id"]

one = connector.read_one(record_id)
many = connector.read_many({"status": "active"})

updated = connector.update_one(record_id, {"status": "inactive"})
replaced = connector.replace_one(record_id, {"name": "replacement"})

deleted = connector.delete_one(record_id, hard=True)
```

## API Notes

- `read_one(record_id)` returns `None` when the record is not found.
- `delete_one(record_id, hard=False)` raises `RuntimeError` because soft delete is not supported by this connector.
- `delete_one(record_id, hard=True)` performs a hard delete and returns:
  - `True` if deleted
  - `False` if the record does not exist

## Testing

Run default tests (excluding external-service integration tests):

```bash
pytest -m "not integration" -q
```

Run integration tests (real Airtable):

```bash
pytest -m integration -q
```

### Integration test environment variables

- `AIRTABLE_API_KEY`
- `AIRTABLE_BASE_ID`
- `AIRTABLE_TABLE_NAME`

If these are not set, integration tests will skip.

## Development

Run all tests:

```bash
pytest -q
```

Run linting/type checks (if configured in your environment):

```bash
ruff check .
pyright
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
