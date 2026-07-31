# Directus Skill

Universal Directus GraphQL CMS client for AI agents. Works with **any** Directus collection — blog posts, CRM leads, custom schemas, etc. Compatible with Directus **10, 11 and 12** (current).

## Features

- **Collection-agnostic** — works with any Directus collection schema
- **Full CRUD** — create, read, update, delete, count operations
- **GraphQL-native** — uses Directus GraphQL API directly
- **Filter operators** — all Directus filter operators supported
- **Collection management** — create/delete collections and fields (admin required)
- **CLI** — command-line interface for ad-hoc operations
- **Type-safe errors** — custom `DirectusError` exception class
- **Directus 12 ready** — soft-delete auto-detects the `status` (legacy) vs `archived` (v12) field, plus a public `ping()` liveness check

## Requirements

- Python 3.9+
- Directus 10, 11 or 12 instance
- API token with appropriate permissions

## Directus Version Compatibility

| Version | Notes |
|---|---|
| **Directus 12.x** | New collections use a boolean `archived` field instead of a string `status`. Soft-delete auto-detects which field a collection has. `/server/health` requires auth — use `ping()` for liveness. |
| **Directus 11.x** | GraphQL primary keys typed as `ID`; requesting missing fields returns errors. |
| **Directus 10.x** | Legacy string `status` soft-delete path. |

## Quick Start

```python
from directus import DirectusClient, DirectusError

client = DirectusClient(
    url="https://your-directus.com",
    token="your_api_token"
)

# Query
records = client.get(
    fields=["id", "title", "status"],
    filters={"status": {"_eq": "published"}},
    limit=10,
    collection="Posts"
)

# Insert
new_record = client.insert(
    {"title": "New Post", "status": "draft"},
    collection="Posts"
)

print(f"Created: {new_record['id']}")
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DIRECTUS_URL` | No | — | Directus instance URL |
| `DIRECTUS_API_TOKEN` | **Yes** | — | API token for CRUD |
| `DIRECTUS_ADMIN_TOKEN` | No | — | Admin scope (collection management) |
| `DIRECTUS_DEFAULT_COLLECTION` | No | — | Optional default collection |

## CLI

```bash
# Query
python -m directus query --collection Posts --fields "id title" --limit 5

# Count
python -m directus count --collection Posts

# Insert
python -m directus insert --collection Posts --data '{"title":"Hello"}'

# Health check
python -m directus health-check

# Public liveness check (Directus 12)
python -m directus ping
```

## Installation

```bash
pip install directus-skill
```

Or clone and use directly:

```python
import sys
sys.path.insert(0, '/path/to/directus-skill')
from directus import DirectusClient
```

## Supported Filter Operators

- `_eq`, `_neq`, `_gt`, `_gte`, `_lt`, `_lte`
- `_in`, `_nin`
- `_null`, `_nnull`, `_empty`, `_nempty`
- `_contains`, `_ncontains`, `_icontains`, `_nicontains`
- `_starts_with`, `_istarts_with`, `_nstarts_with`, `_nistarts_with`
- `_ends_with`, `_iends_with`, `_nends_with`, `_niends_with`
- `_between`, `_nbetween`
- `_json`, `_some`, `_none`
- Logical grouping: `_and`, `_or`

## Soft-Delete (Directus 12)

`client.delete(id, hard=False)` auto-detects the collection's archive field:
- legacy collections with a `status` field → sets `status = "Removed"`
- Directus 12+ collections with an `archived` boolean → sets `archived = true`

Override with `archive_field=` / `archive_value=` if needed. Hard delete (`hard=True`) permanently removes the record.

## Full Documentation

See [SKILL.md](SKILL.md) for complete documentation including:
- Collection management API
- Error handling
- CLI options
- Edge cases and known issues

## License

MIT