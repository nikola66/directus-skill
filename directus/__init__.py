"""
Directus GraphQL Client — universal CRUD for any Directus collection.

Environment
-----------
DIRECTUS_URL
    Base URL of the Directus instance.

DIRECTUS_API_TOKEN (required)
    API token for read/write operations.

DIRECTUS_ADMIN_TOKEN
    Token with admin scope for collection creation/deletion.
    Falls back to DIRECTUS_API_TOKEN if not set.

DIRECTUS_DEFAULT_COLLECTION
    Optional default collection name.

Quick Start
-----------
    from directus import DirectusClient

    client = DirectusClient()

    # CRUD
    record = client.insert({'title': 'Hello'}, collection='Posts')
    results = client.get(fields=['id', 'title'], limit=10, collection='Posts')
    client.update(id, {'status': 'draft'}, collection='Posts')
    client.delete(id, collection='Posts')

    # CLI
    python -m directus query --collection Posts --fields id title --limit 5
    python -m directus count --collection Posts
    python -m directus insert --collection Posts --data '{"title":"New"}'

Exports
------
    DirectusClient    — main client class
    DirectusError   — typed exception with message, details, status_code
"""

from .client import DirectusClient, DirectusError

__all__ = [
    'DirectusClient',
    'DirectusError',
]

__version__ = '1.4.0'
