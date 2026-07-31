---
name: directus
description: Universal Directus GraphQL CMS client for CRUD operations on any collection (Directus 10/11/12)
---

# Directus Skill — Universal CMS Operations

## Overview

Universal Directus GraphQL client for **any** Directus collection schema. Works with any collection — from CRM leads to blog posts to custom schemas. Compatible with Directus **10, 11 and 12** (current).

## Directus Version Compatibility

| Version | Status | Notes |
|---|---|---|
| Directus 12.x | Current | New collections use a boolean `archived` field instead of a string `status`. Soft-delete auto-detects which field a collection has. `/server/health` requires auth — use `ping()` for liveness. `?version=published` replaces `?version=main`. |
| Directus 11.x | Supported | GraphQL primary keys are typed `ID` (client passes inline literals — no change needed). Missing fields in requests now return errors. |
| Directus 10.x | Supported | Legacy string `status` soft-delete path. |

Key v12 notes:
- **`archived` vs `status`** — Collections created in Directus 12 default to a boolean `archived` field. `client.delete(id, hard=False)` automatically detects whether a collection uses `status` (sets `'Removed'`) or `archived` (sets `true`). Override with `archive_field=` / `archive_value=` if needed.
- **Versioned collections** — Query published items with `?version=published` (v12); `main` still works for backward compatibility.
- **License enforcement** — When an instance exceeds Core tier limits, the GraphQL API is disabled. Check `ping()`/`health_check()` first if operations start failing with authorization errors.
- **Liveness checks** — `/server/health` is restricted to authenticated users in v12; use `client.ping()` (`GET /server/ping`) for public liveness.

## Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DIRECTUS_URL` | No | `https://hub.aratech.ae` | Directus instance URL |
| `DIRECTUS_API_TOKEN` | **Yes** | — | API token for read/write operations |
| `DIRECTUS_ADMIN_TOKEN` | For admin ops | — | Admin scope token for collection/field management |
| `DIRECTUS_DEFAULT_COLLECTION` | No | — | Default collection name (optional) |

## Installation

```bash
pip install directus-skill
```

Or use directly as a skill module:

```python
# Add to Python path
import sys
sys.path.insert(0, '/path/to/directus-skill')

from directus import DirectusClient, DirectusError

client = DirectusClient(
    url="https://your-directus-instance.com",
    token="your_api_token_here"
)
```

## Core API

### Instantiation

```python
from directus import DirectusClient

# Default client (reads from env vars)
client = DirectusClient()

# Explicit configuration
client = DirectusClient(
    url="https://hub.aratech.ae",
    token="your_api_token",
    admin_token="your_admin_token",  # only for collection/field management
    collection="Authors"             # optional default collection
)
```

### CRUD Operations

```python
# Create / Insert
record = client.insert(
    {'name': 'Alice', 'slug': 'alice', 'status': 'published'},
    collection='Authors'
)
record_id = record.get('id')

# Read / Query multiple
results = client.get(
    fields=['id', 'name', 'status'],
    filters={'status': {'_eq': 'published'}},
    sort=['name_ASC'],
    limit=10,
    offset=0,
    collection='Authors'
)

# Read / Query single
one = client.get_one(
    fields=['id', '*'],
    filters={'id': {'_eq': '123'}},
    collection='Authors'
)

# Update
client.update(
    record_id,
    {'status': 'draft'},
    collection='Authors'
)

# Delete
client.delete(record_id, hard=False, collection='Authors')  # soft-delete
client.delete(record_id, hard=True, collection='Authors')   # permanent

# Soft-delete auto-detects the archive field:
#   - legacy collections: status = 'Removed'
#   - Directus 12+ collections: archived = true
# Override the detection explicitly if needed:
client.delete(record_id, hard=False, collection='Authors',
              archive_field='archived', archive_value=True)

# Count
total = client.count(
    filters={'status': {'_eq': 'published'}},
    collection='Authors'
)
```

### Health Check

```python
if client.health_check():
    print("Directus is reachable and token is valid")

# Public liveness check (Directus 12: /server/health now requires auth)
if client.ping():
    print("Directus server is up")
```

### Domain Helpers (Lead-oriented, adaptable)

These helpers are opinionated for CRM lead tracking but work with any schema by
passing field names. For Directus 12 collections that use the boolean `archived`
field instead of a string `status`, set `status_is_boolean=True`.

```python
# Did we already contact this email?
client.is_contacted('alice@example.com')
client.is_contacted('alice@example.com', status_field='archived', status_is_boolean=True)

# All contacted email addresses / domains
client.get_contacted_emails()
client.get_contacted_domains(status_field='archived', status_is_boolean=True)

# Records with duplicate values for a field
client.find_duplicates(field='Lead_Email')
```

## Filter Operators

All Directus filter operators are supported (Directus 11/12 list):

| Operator | Description | Example |
|---|---|---|
| `_eq` | Equals | `{'status': {'_eq': 'published'}}` |
| `_neq` | Not equals | `{'status': {'_neq': 'draft'}}` |
| `_lt`, `_lte` | Less than (or equal) | `{'views': {'_lte': 50}}` |
| `_gt`, `_gte` | Greater than (or equal) | `{'views': {'_gte': 100}}` |
| `_in` | Is one of | `{'status': {'_in': ['draft', 'published']}}` |
| `_nin` | Is not one of | `{'status': {'_nin': ['archived']}}` |
| `_null` | Is null | `{'email': {'_null': True}}` |
| `_nnull` | Is not null | `{'email': {'_nnull': True}}` |
| `_contains` | Contains | `{'name': {'_contains': 'alice'}}` |
| `_ncontains` | Does not contain | `{'name': {'_ncontains': 'spam'}}` |
| `_icontains` | Contains (case-insensitive) | `{'name': {'_icontains': 'ALICE'}}` |
| `_nicontains` | Does not contain (case-insensitive) | `{'name': {'_nicontains': 'BOT'}}` |
| `_starts_with` | Starts with | `{'slug': {'_starts_with': 'al'}}` |
| `_istarts_with` | Starts with (case-insensitive) | `{'slug': {'_istarts_with': 'AL'}}` |
| `_nstarts_with` | Does not start with | `{'slug': {'_nstarts_with': 'x'}}` |
| `_nistarts_with` | Does not start with (case-insensitive) | `{'slug': {'_nistarts_with': 'X'}}` |
| `_ends_with` | Ends with | `{'slug': {'_ends_with': 'ce'}}` |
| `_iends_with` | Ends with (case-insensitive) | `{'slug': {'_iends_with': 'CE'}}` |
| `_nends_with` | Does not end with | `{'slug': {'_nends_with': 'x'}}` |
| `_niends_with` | Does not end with (case-insensitive) | `{'slug': {'_niends_with': 'X'}}` |
| `_between` | Between two values (inclusive) | `{'views': {'_between': [10, 100]}}` |
| `_nbetween` | Not between two values | `{'views': {'_nbetween': [10, 100]}}` |
| `_empty` | Is empty (`null` or falsy) | `{'name': {'_empty': True}}` |
| `_nempty` | Is not empty | `{'name': {'_nempty': True}}` |
| `_json` | Compare values inside a JSON document | `{'metadata': {'_json': {'email': 'x@y.com'}}}` |
| `_some` | At least one related value matches | `{'categories': {'_some': {'name': {'_eq': 'Recipe'}}}}` |
| `_none` | No related values match | `{'categories': {'_none': {'name': {'_eq': 'Recipe'}}}}` |

Notes:
- Geometry operators (`_intersects`, `_nintersects`, `_intersects_bbox`, `_nintersects_bbox`) apply to geometry fields only.
- `_regex` is available in validation rules and permissions.
- Combine rules with the `_and` / `_or` logical operators: `{'_or': [{...}, {...}]}`.
- Relational filters work by nesting field names, e.g. `{'author': {'name': {'_eq': 'Alice'}}}`.

## Collection Management (Admin)

```python
# Requires ADMIN_TOKEN

# List all collections
cols = client.get_collections()

# Get collection schema (fields)
schema = client.get_collection_schema('Authors')

# Create collection
# Directus 12 note: collections without an explicit 'status' string field get a
# boolean 'archived' field. Include a 'status' field for legacy behavior, or an
# 'archived' boolean to match Directus 12 defaults.
client.create_collection('Books', fields=[
    {
        'field': 'id',
        'type': 'integer',
        'meta': {'hidden': True, 'interface': 'numeric', 'readonly': True},
        'schema': {'is_primary_key': True, 'has_auto_increment': True}
    },
    {
        'field': 'title',
        'type': 'string',
        'meta': {'interface': 'input'},
        'schema': {}
    },
    {
        'field': 'archived',
        'type': 'boolean',
        'meta': {'interface': 'boolean', 'default': False},
        'schema': {}
    },
    {
        'field': 'description',
        'type': 'text',
        'meta': {'interface': 'textarea'},
        'schema': {}
    }
])

# Add field to existing collection
client.create_field('Authors', 'bio', 'text',
    meta={'interface': 'textarea'})

# Delete collection
client.delete_collection('Old_Collection', hard=False)  # soft
client.delete_collection('Old_Collection', hard=True)     # permanent
```

## Error Handling

```python
from directus import DirectusError

try:
    client.insert(data, collection='X')
except DirectusError as e:
    print(e.message)       # Human-readable error message
    print(e.details)      # Full API response / error details
    print(e.status_code) # HTTP status or GraphQL error code
```

## CLI Usage

```bash
# Query records
python -m directus query \
  --collection Authors \
  --fields "id name status" \
  --filters '{"status":{"_eq":"published"}}' \
  --limit 20

# Count records
python -m directus count --collection Authors

# Insert record
python -m directus insert \
  --collection Authors \
  --data '{"name":"New Author","slug":"new-author"}'

# Update record
python -m directus update \
  --collection Authors \
  --id 123 \
  --data '{"status":"draft"}'

# Delete record
python -m directus delete --collection Authors --id 123
# Soft-delete field overrides (auto-detected by default):
python -m directus delete --collection Authors --id 123 --soft-field archived --soft-value true

# Health check (authenticated GraphQL check)
python -m directus health-check

# Public liveness check (Directus 12: use this instead of /server/health)
python -m directus ping

# List collections
python -m directus collections
```

**With custom URL/token:**
```bash
DIRECTUS_URL=https://your-instance.com DIRECTUS_API_TOKEN=xxx python -m directus query ...
```

## Edge Cases

| Situation | Behavior |
|---|---|
| Non-existent record delete | Returns `True` (GraphQL returns `id` regardless) |
| Soft-delete with no archive field | Raises `DirectusError` — pass `archive_field=`/`archive_value=` or use `hard=True` |
| Requesting non-existent fields (v11+) | Raises `DirectusError` (Directus 11+ rejects missing fields) |
| Unicode content | Full UTF-8 support |
| Null field values | Pass `None` in Python, `null` in JSON |
| Empty strings | Stored as `''` |
| 204 No Content | Handled gracefully, returns `{}` |
| ID as string vs integer | GraphQL returns IDs as strings; cast as needed |
| Versioned collections (v12) | Use `?version=published` (previously `main`) |
| GraphQL PK types (v11+) | Typed as `ID`; client passes inline literals, so no changes needed |

## Payload Structure Notes

When creating collections via API, **both** collection-level and field-level require `schema` and `meta` keys:

```python
{
    'collection': 'my_collection',
    'schema': {},
    'meta': {},
    'fields': [
        {
            'field': 'id',
            'type': 'integer',
            'meta': {'hidden': True, 'interface': 'numeric'},
            'schema': {'is_primary_key': True, 'has_auto_increment': True}
        }
    ]
}
```

Omitting either causes misleading 403 Forbidden errors.

**Directus 12 soft-delete payload**: `delete(id, hard=False)` sets `status: "Removed"` on legacy collections, or `archived: true` on v12 collections. Both forms use the `update_<collection>_item` mutation.