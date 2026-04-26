---
name: directus
description: Universal Directus GraphQL CMS client for CRUD operations on any collection
---

# Directus Skill — Universal CMS Operations

## Overview

Universal Directus GraphQL client for **any** Directus collection schema. Works with any collection — from CRM leads to blog posts to custom schemas.

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
```

## Filter Operators

All Directus filter operators are supported:

| Operator | Description | Example |
|---|---|---|
| `_eq` | Equals | `{'status': {'_eq': 'published'}}` |
| `_neq` | Not equals | `{'status': {'_neq': 'draft'}}` |
| `_contains` | Contains (case-sensitive) | `{'name': {'_contains': 'alice'}}` |
| `_icontains` | Contains (case-insensitive) | `{'name': {'_icontains': 'ALICE'}}` |
| `_starts_with` | Starts with | `{'slug': {'_starts_with': 'al'}}` |
| `_ends_with` | Ends with | `{'slug': {'_ends_with': 'ce'}}` |
| `_in` | In array | `{'status': {'_in': ['draft', 'published']}}` |
| `_nin` | Not in array | `{'status': {'_nin': ['archived']}}` |
| `_null` | Is null | `{'email': {'_null': True}}` |
| `_nnull` | Is not null | `{'email': {'_nnull': True}}` |
| `_empty` | Is empty string | `{'name': {'_empty': True}}` |
| `_nempty` | Is not empty | `{'name': {'_nempty': True}}` |
| `_gt`, `_gte` | Greater than (or equal) | `{'views': {'_gte': 100}}` |
| `_lt`, `_lte` | Less than (or equal) | `{'views': {'_lte': 50}}` |

## Collection Management (Admin)

```python
# Requires ADMIN_TOKEN

# List all collections
cols = client.get_collections()

# Get collection schema (fields)
schema = client.get_collection_schema('Authors')

# Create collection
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

# Health check
python -m directus health-check

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
| Unicode content | Full UTF-8 support |
| Null field values | Pass `None` in Python, `null` in JSON |
| Empty strings | Stored as `''` |
| 204 No Content | Handled gracefully, returns `{}` |
| ID as string vs integer | GraphQL returns IDs as strings; cast as needed |

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