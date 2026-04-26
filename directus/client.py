#!/usr/bin/env python3
"""
Directus GraphQL Client — generic CRUD operations for any collection.

This is a universal Directus client that works with any collection schema.
Previously hardcoded for CRM 'Leads' — now fully collection-agnostic.

Usage:
    from directus.client import DirectusClient

    # Per-collection client
    authors = DirectusClient(collection='Blog_Authors')
    post_id = authors.insert({'name': 'Alice', 'slug': 'alice', 'status': 'published'})['id']

    # Generic client with collection override per call
    client = DirectusClient()
    client.insert(collection='Posts', data={'title': 'Hello', 'status': 'published'})

    # Filtering, pagination, sorting
    results = client.get(
        fields=['id', 'title', 'status'],
        filters={'status': {'_eq': 'published'}},
        sort=['date_created_DESC'],
        limit=10,
        collection='Posts'
    )

Domain helpers (is_contacted, find_duplicates) are Lead-specific by default.
They accept custom field names to adapt to other schemas.
"""

import os, sys, json, ssl, urllib.request, urllib.error
from typing import Optional, Dict, List, Set, Any
from dataclasses import dataclass

DIRECTUS_URL = os.getenv('DIRECTUS_URL') or os.getenv('DIRECTUS_API_URL', 'https://hub.aratech.ae')
API_TOKEN = os.getenv('DIRECTUS_API_TOKEN')
ADMIN_TOKEN = os.getenv('DIRECTUS_ADMIN_TOKEN')
DEFAULT_COLLECTION = os.getenv('DIRECTUS_DEFAULT_COLLECTION')
USER_AGENT = 'Directus-Skill/1.0'


@dataclass
class DirectusError(Exception):
    message: str
    details: Optional[Any] = None
    status_code: Optional[int] = None

    def __str__(self):
        if self.details:
            return f"{self.message} | {self.details}"
        return self.message


class DirectusClient:
    """Universal Directus GraphQL client for any collection."""

    def __init__(self, url: str = None, token: str = None, admin_token: str = None, collection: str = None):
        self.url = (url or DIRECTUS_URL or 'https://hub.aratech.ae').rstrip('/')
        self.token = token or API_TOKEN
        self.admin_token = admin_token or ADMIN_TOKEN
        self.default_collection = collection or DEFAULT_COLLECTION
        
        if not self.token:
            raise DirectusError(
                message="DIRECTUS_API_TOKEN is required",
                details="Set the DIRECTUS_API_TOKEN environment variable or pass token= to DirectusClient()",
                status_code=None
            )

    # ─── Internal ──────────────────────────────────────────────────────────────

    def _graphql(self, query: str, variables: Optional[Dict] = None, timeout: int = 30) -> Dict:
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        req = urllib.request.Request(
            f'{self.url}/graphql',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.token}',
                'User-Agent': USER_AGENT
            },
            method='POST'
        )
        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
                if 'errors' in data:
                    err = data['errors'][0]
                    raise DirectusError(
                        message=err.get('message', 'GraphQL error'),
                        details=err.get('extensions', {}),
                        status_code=err.get('extensions', {}).get('code')
                    )
                return data.get('data', {})
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                body_parsed = json.loads(body)
                msg = body_parsed.get('errors', [{}])[0].get('message', body[:200])
            except Exception:
                msg = body[:200]
            raise DirectusError(message=f"HTTP {e.code}", details=msg, status_code=e.code)
        except Exception as e:
            raise DirectusError(message=str(e))

    def _resolve_collection(self, collection: str = None) -> str:
        return collection or self.default_collection

    def _to_graphql_value(self, v: Any) -> str:
        if v is None:
            return 'null'
        if isinstance(v, bool):
            return 'true' if v else 'false'
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, str):
            escaped = v.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return f'"{escaped}"'
        if isinstance(v, list):
            items = ', '.join(self._to_graphql_value(i) for i in v)
            return f'[{items}]'
        if isinstance(v, dict):
            inner = ', '.join(f'{k}: {self._to_graphql_value(val)}' for k, val in v.items())
            return '{ ' + inner + ' }'
        return f'"{str(v)}"'

    def _build_args(self, filters=None, limit=None, offset=None, sort=None) -> str:
        parts = []
        if filters:
            parts.append(f'filter: {self._render_filters(filters)}')
        if limit is not None:
            parts.append(f'limit: {limit}')
        if offset is not None:
            parts.append(f'offset: {offset}')
        if sort:
            sort_normalized = []
            for s in sort:
                s_upper = s.upper()
                if s_upper.endswith('_DESC'):
                    sort_normalized.append('-' + s[:-5])
                elif s_upper.endswith('_ASC'):
                    sort_normalized.append(s[:-4])
                else:
                    sort_normalized.append(s)
            parts.append(f'sort: {json.dumps(sort_normalized)}')
        return ', '.join(parts)

    def _render_filters(self, filters: Dict) -> str:
        if not filters:
            return '{}'
        lines = []
        for key, value in filters.items():
            lines.append(self._render_filter_pair(key, value))
        return '{\n' + '\n'.join(lines) + '\n}'

    def _render_filter_pair(self, key: str, value) -> str:
        if isinstance(value, dict):
            inner = ', '.join(f'{k}: {json.dumps(v)}' for k, v in value.items())
            return f'  {key}: {{{inner}}}'
        return f'  {key}: {json.dumps(value)}'

    # ─── CRUD ───────────────────────────────────────────────────────────────────

    def get(self, fields: List[str], filters: Optional[Dict] = None,
            limit: Optional[int] = None, offset: Optional[int] = None,
            sort: Optional[List[str]] = None,
            collection: str = None) -> List[Dict]:
        """Fetch multiple records from any collection."""
        coll = self._resolve_collection(collection)
        field_str = ' '.join(fields)
        args = self._build_args(filters, limit, offset, sort)
        query = f'query {{ {coll}({args}) {{ {field_str} }} }}' if args else f'query {{ {coll} {{ {field_str} }} }}'
        result = self._graphql(query)
        return result.get(coll, [])

    def get_one(self, fields: List[str], filters: Dict,
                 collection: str = None) -> Optional[Dict]:
        """Fetch a single record matching filters."""
        records = self.get(fields, filters=filters, limit=1, collection=collection)
        return records[0] if records else None

    def insert(self, data: Dict, collection: str = None) -> Dict:
        """Create a new record. Returns {'id': <new_id>}."""
        coll = self._resolve_collection(collection)
        pairs = [f'{key}: {self._to_graphql_value(val)}' for key, val in data.items()]
        data_str = '{ ' + ', '.join(pairs) + ' }'
        query = f'mutation {{ create_{coll}_item(data: {data_str}) {{ id }} }}'
        result = self._graphql(query)
        return result.get(f'create_{coll}_item', {})

    def update(self, id: str, data: Dict, collection: str = None) -> Dict:
        """Update an existing record by ID. Returns {'id': id}."""
        coll = self._resolve_collection(collection)
        pairs = [f'{key}: {self._to_graphql_value(val)}' for key, val in data.items()]
        data_str = '{ ' + ', '.join(pairs) + ' }'
        query = f'mutation {{ update_{coll}_item(id: "{id}", data: {data_str}) {{ id }} }}'
        result = self._graphql(query)
        return result.get(f'update_{coll}_item', {})

    def delete(self, id: str, hard: bool = False, collection: str = None) -> bool:
        """
        Delete a record.
        hard=False (default): soft-delete by setting status='Removed' (only works if collection has 'status' field)
        hard=True: permanently delete via API
        """
        coll = self._resolve_collection(collection)
        if hard:
            query = f'mutation {{ delete_{coll}_item(id: "{id}") {{ id }} }}'
        else:
            query = f'mutation {{ update_{coll}_item(id: "{id}", data: {{ status: "Removed" }}) {{ id }} }}'
        result = self._graphql(query)
        key = f'delete_{coll}_item' if hard else f'update_{coll}_item'
        return 'id' in result.get(key, {})

    def count(self, filters: Optional[Dict] = None, collection: str = None) -> int:
        """Return total record count, optionally filtered."""
        coll = self._resolve_collection(collection)
        args = self._build_args(filters)
        query = f'query {{ {coll}_aggregated({args}) {{ count {{ id }} }} }}' if args else \
                f'query {{ {coll}_aggregated {{ count {{ id }} }} }}'
        result = self._graphql(query)
        agg = result.get(f'{coll}_aggregated', [])
        if not agg:
            return 0
        return agg[0].get('count', {}).get('id', 0) or 0

    # ─── Domain helpers — Lead collection default ───────────────────────────────
    # These methods are opinionated for CRM lead tracking. They work with any
    # collection IF you pass the correct field names via parameters.

    def is_contacted(self, email: str,
                     email_field: str = 'Lead_Email',
                     status_field: str = 'status',
                     status_contains: str = 'Contacted',
                     collection: str = None) -> bool:
        """Check if an email exists with status containing the given keyword."""
        coll = self._resolve_collection(collection)
        records = self.get(
            fields=['id', status_field],
            filters={email_field: {'_eq': email.lower()}},
            limit=5,
            collection=coll
        )
        return any(status_contains in rec.get(status_field, '') for rec in records)

    def get_contacted_emails(self,
                             email_field: str = 'Lead_Email',
                             status_field: str = 'status',
                             status_contains: str = 'Contacted',
                             collection: str = None) -> Set[str]:
        """All unique email addresses where status contains keyword."""
        coll = self._resolve_collection(collection)
        query = f'query {{ {coll}(filter: {{{status_field}: {{_contains: "{status_contains}"}}}}) {{ {email_field} }} }}'
        result = self._graphql(query)
        emails = set()
        for rec in result.get(coll, []):
            email = rec.get(email_field, '') or ''
            if '@' in email:
                emails.add(email.lower())
        return emails

    def get_contacted_domains(self,
                              email_field: str = 'Lead_Email',
                              website_field: str = 'Lead_Website',
                              status_field: str = 'status',
                              status_contains: str = 'Contacted',
                              collection: str = None) -> Set[str]:
        """Extract unique domains from contacted records (email + website)."""
        emails = self.get_contacted_emails(email_field, status_field, status_contains, collection)
        domains = {e.split('@')[1].lower() for e in emails if '@' in e}
        coll = self._resolve_collection(collection)
        query = f'query {{ {coll}(filter: {{{status_field}: {{_contains: "{status_contains}"}}}}) {{ {website_field} }} }}'
        result = self._graphql(query)
        for rec in result.get(coll, []):
            website = rec.get(website_field, '') or ''
            if website:
                domain = website.lower().replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0]
                if domain:
                    domains.add(domain)
        return domains

    def find_duplicates(self, field: str = 'Lead_Email',
                        collection: str = None) -> Dict[str, List[Dict]]:
        """
        Find records with duplicate values for a given field.
        Defaults to email deduping for Lead-style schemas.
        """
        coll = self._resolve_collection(collection)
        all_records = self.get(fields=['id', field], collection=coll)
        duplicates = {}
        seen = {}
        for rec in all_records:
            val = str(rec.get(field, '') or '').lower().strip()
            if not val:
                continue
            if val in seen:
                duplicates.setdefault(val, [seen[val]]).append(rec)
            else:
                seen[val] = rec
        return duplicates

    # ─── Utilities ──────────────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """Verify Directus instance is reachable and API token is valid."""
        try:
            self._graphql('query { __typename }')
            return True
        except DirectusError:
            return False

    # ─── Collection Management (Admin) ──────────────────────────────────────────
    # These require an admin-scoped token. They operate via the REST v2 admin API.

    def _rest(self, endpoint: str, method: str = 'POST', body: Dict = None) -> Dict:
        """Make a direct REST v2 call (used for admin operations)."""
        url = f'{self.url}/{endpoint}'
        data = json.dumps(body).encode('utf-8') if body else None
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.admin_token or self.token}',
                'User-Agent': USER_AGENT
            },
            method=method
        )
        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                resp_body = resp.read().decode()
                return json.loads(resp_body) if resp_body.strip() else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                msg = json.loads(body).get('errors', [{}])[0].get('message', body[:200])
            except Exception:
                msg = body[:200]
            raise DirectusError(message=f'REST {e.code}', details=msg, status_code=e.code)
        except Exception as e:
            raise DirectusError(message=str(e))

    def get_collections(self) -> List[str]:
        """List all collection names in the project."""
        result = self._rest('collections', 'GET')
        return [c['collection'] for c in result.get('data', [])]

    def get_collection_schema(self, collection: str) -> Dict:
        """Return full schema (fields, meta) for a collection."""
        return self._rest(f'fields/{collection}', 'GET')

    def create_collection(self, collection: str, fields: List[Dict] = None, meta: Dict = None) -> Dict:
        """
        Create a new collection (requires admin token).

        Payload structure is strict — both collection-level and field-level must
        include 'schema' and 'meta' keys, otherwise Directus returns 403 FORBIDDEN.

        Args:
            collection: Name of the collection to create
            fields: Optional list of field definitions. Each dict must contain:
                - 'field': field name
                - 'type': Directus type ('string', 'integer', 'boolean', 'datetime', etc.)
                - 'meta': dict of interface options (can be {})
                - 'schema': dict of database options (can be {})
            meta: Optional collection-level metadata dict

        Returns:
            API response dict

        Example:
            client.create_collection('TEST_Items', fields=[
                {'field': 'id', 'type': 'integer',
                 'meta': {'hidden': True, 'interface': 'numeric', 'readonly': True},
                 'schema': {'is_primary_key': True, 'has_auto_increment': True}},
                {'field': 'name', 'type': 'string',
                 'meta': {'interface': 'input'},
                 'schema': {}}
            ])
        """
        payload = {
            'collection': collection,
            'schema': {},
            'meta': meta or {},
            'fields': []
        }
        if fields:
            for f in fields:
                payload['fields'].append({
                    'field': f['field'],
                    'type': f['type'],
                    'meta': f.get('meta', {}),
                    'schema': f.get('schema', {})
                })
        return self._rest('collections', 'POST', payload)

    def create_field(self, collection: str, field: str, field_type: str,
                     meta: Dict = None, schema: Dict = None) -> Dict:
        """Add a new field to an existing collection (admin required)."""
        payload = {
            'field': field,
            'type': field_type,
            'meta': meta or {},
            'schema': schema or {}
        }
        return self._rest(f'fields/{collection}', 'POST', payload)

    def delete_collection(self, collection: str, hard: bool = False) -> bool:
        """
        Delete a collection.
        hard=False (default): soft-delete by sending to trash (if supported).
        hard=True: permanently delete. Both require the collection to be empty.
        """
        try:
            self._rest(f'collections/{collection}', 'DELETE')
            return True
        except DirectusError as e:
            # 409 = collection not empty or cannot be deleted
            if e.status_code == 409:
                return False
            raise

    # ─── Domain helpers — Lead collection default ───────────────────────────────
# Singleton for legacy code
_client = None


def get_client() -> DirectusClient:
    global _client
    if _client is None:
        _client = DirectusClient()
    return _client
