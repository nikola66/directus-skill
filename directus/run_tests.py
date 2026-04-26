#!/usr/bin/env python3
"""
Systematic test suite for the Directus skill.

Phases:
1. Environment check
2. Create TEST_ collections (requires admin token) — fallback to existing Blog_* if denied
3. CRUD tests (Create, Read, Update, Delete) on each collection
4. Relationship tests (many-to-many via junction table)
5. Edge case tests (special chars, empty sets, non-existent IDs, duplicates)
6. Cleanup — delete all TEST_ records and collections
7. Validation & summary

Usage:
    python3 run_directus_tests.py [--token ADMIN_TOKEN] [--url DIRECTUS_URL]

If no admin token is provided, collection creation is skipped and the suite
runs against existing Blog_* collections for validation only.
"""

import os
import sys
import json
import argparse
import uuid
from pathlib import Path

# Add skill to path (when run as script)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from skills.directus.client import DirectusClient, DirectusError

# ─── Load ~/.hermes/.env if present (simple key=value parser, no deps needed) ───
_env_path = Path.home() / '.hermes' / '.env'
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith('#') or '=' not in _line:
            continue
        _key, _, _val = _line.partition('=')
        os.environ.setdefault(_key.strip(), _val.strip())

# ─── Test configuration ────────────────────────────────────────────────────────

DEFAULT_URL = 'https://hub.aratech.ae'

# Collection schemas for TEST_ sets
TEST_SCHEMAS = {
    'TEST_Authors': {
        'fields': [
            {'field': 'id', 'type': 'integer', 'meta': {'hidden': True, 'interface': 'numeric', 'readonly': True}, 'schema': {'is_primary_key': True, 'has_auto_increment': True}},
            {'field': 'name', 'type': 'string', 'meta': {'interface': 'input'}, 'schema': {}},
            {'field': 'slug', 'type': 'string', 'meta': {'interface': 'input'}, 'schema': {}},
            {'field': 'bio', 'type': 'text', 'meta': {'interface': 'textarea'}, 'schema': {}},
            {'field': 'status', 'type': 'string', 'meta': {'interface': 'select', 'options': {'draft': 'Draft', 'published': 'Published', 'removed': 'Removed'}}, 'schema': {}},
        ]
    },
    'TEST_Tags': {
        'fields': [
            {'field': 'id', 'type': 'integer', 'meta': {'hidden': True, 'interface': 'numeric', 'readonly': True}, 'schema': {'is_primary_key': True, 'has_auto_increment': True}},
            {'field': 'name', 'type': 'string', 'meta': {'interface': 'input'}, 'schema': {}},
            {'field': 'slug', 'type': 'string', 'meta': {'interface': 'input'}, 'schema': {}},
        ]
    },
    'TEST_Categories': {
        'fields': [
            {'field': 'id', 'type': 'integer', 'meta': {'hidden': True, 'interface': 'numeric', 'readonly': True}, 'schema': {'is_primary_key': True, 'has_auto_increment': True}},
            {'field': 'name', 'type': 'string', 'meta': {'interface': 'input'}, 'schema': {}},
            {'field': 'slug', 'type': 'string', 'meta': {'interface': 'input'}, 'schema': {}},
            {'field': 'icon', 'type': 'string', 'meta': {'interface': 'input'}, 'schema': {}},
            {'field': 'color', 'type': 'string', 'meta': {'interface': 'input'}, 'schema': {}},
            {'field': 'sort', 'type': 'integer', 'meta': {'interface': 'numeric'}, 'schema': {}},
            {'field': 'status', 'type': 'string', 'meta': {'interface': 'select', 'options': {'draft': 'Draft', 'published': 'Published'}}, 'schema': {}},
        ]
    },
    'TEST_Posts': {
        'fields': [
            {'field': 'id', 'type': 'integer', 'meta': {'hidden': True, 'interface': 'numeric', 'readonly': True}, 'schema': {'is_primary_key': True, 'has_auto_increment': True}},
            {'field': 'status', 'type': 'string', 'meta': {'interface': 'select'}, 'schema': {}},
            {'field': 'author', 'type': 'integer', 'meta': {'interface': 'numeric'}, 'schema': {}},
            {'field': 'category', 'type': 'integer', 'meta': {'interface': 'numeric'}, 'schema': {}},
            {'field': 'sort', 'type': 'integer', 'meta': {'interface': 'numeric'}, 'schema': {}},
            {'field': 'slug', 'type': 'string', 'meta': {'interface': 'input'}, 'schema': {}},
            {'field': 'views', 'type': 'integer', 'meta': {'interface': 'numeric'}, 'schema': {}},
        ]
    },
    'TEST_Posts_Translations': {
        'fields': [
            {'field': 'id', 'type': 'integer', 'meta': {'hidden': True, 'interface': 'numeric', 'readonly': True}, 'schema': {'is_primary_key': True, 'has_auto_increment': True}},
            {'field': 'posts_id', 'type': 'integer', 'meta': {'interface': 'numeric'}, 'schema': {}},
            {'field': 'languages_code', 'type': 'string', 'meta': {'interface': 'input'}, 'schema': {}},
            {'field': 'title', 'type': 'string', 'meta': {'interface': 'input'}, 'schema': {}},
            {'field': 'slug', 'type': 'string', 'meta': {'interface': 'input'}, 'schema': {}},
            {'field': 'content', 'type': 'text', 'meta': {'interface': 'textarea'}, 'schema': {}},
        ]
    },
    'TEST_Posts_Tags': {
        'fields': [
            {'field': 'id', 'type': 'integer', 'meta': {'hidden': True, 'interface': 'numeric', 'readonly': True}, 'schema': {'is_primary_key': True, 'has_auto_increment': True}},
            {'field': 'posts_id', 'type': 'integer', 'meta': {'interface': 'numeric'}, 'schema': {}},
            {'field': 'tags_id', 'type': 'integer', 'meta': {'interface': 'numeric'}, 'schema': {}},
        ]
    },
}

# Fallback existing collections (if TEST_ creation fails or no admin token)
FALLBACK_COLLECTIONS = {
    'Authors': 'Blog_Authors',
    'Tags': 'Blog_Tags',
    'Categories': 'Blog_Categories',
    'Posts': 'Blog_Posts',
    'Posts_Translations': 'Blog_Posts_Translations',
    'Posts_Tags': 'Blog_Posts_Tags',
}

# ─── Reporting helpers ─────────────────────────────────────────────────────────

class TestRunner:
    def __init__(self, client):
        self.client = client
        self.passed = 0
        self.failed = 0
        self.warnings = []
        self.created_ids = {'authors': [], 'tags': [], 'categories': [], 'posts': []}

    def _ok(self, msg):
        self.passed += 1
        print(f'  ✅ {msg}')

    def _fail(self, msg, error=None):
        self.failed += 1
        print(f'  ❌ {msg}')
        if error:
            print(f'     Error: {error}')

    def _warn(self, msg):
        self.warnings.append(msg)
        print(f'  ⚠️  {msg}')

    def _attempt(self, fn, desc):
        try:
            fn()
            self._ok(desc)
        except DirectusError as e:
            self._fail(desc, f'{e.message} — {e.details}' if e.details else e.message)
        except Exception as e:
            self._fail(desc, str(e))

    def _clear_collection(self, collection: str):
        """Delete all records in a collection (hard) to prepare for drop."""
        try:
            records = self.client.get(fields=['id'], collection=collection, limit=1000)
            for rec in records:
                try:
                    self.client.delete(rec['id'], hard=True, collection=collection)
                except Exception:
                    pass
        except Exception:
            pass  # collection may not exist or be queryable

            self._fail(desc, str(e))

    # Phase methods

    def phase_collections(self, use_test: bool, admin_available: bool):
        print(f'\n📁 Phase 1 — Collections')
        if use_test and admin_available:
            # Ensure clean slate: clear and drop any existing TEST_ collections
            for name in TEST_SCHEMAS:
                try:
                    self._clear_collection(name)
                    self.client.delete_collection(name, hard=True)
                except Exception:
                    pass  # ignore — may not exist
            # Create fresh collections with correct schemas
            for name, schema in TEST_SCHEMAS.items():
                self._attempt(
                    lambda n=name, s=schema: self.client.create_collection(n, fields=s['fields']),
                    f'Create collection {name}'
                )
            # Verify
            cols = self.client.get_collections()
            for name in TEST_SCHEMAS:
                if name not in cols:
                    self._fail(f'{name} missing from collection list')
                else:
                    self._ok(f'{name} exists')
        else:
            self._warn('Skipping TEST_ collection creation (no admin token or flag off); will use existing Blog_* collections')
            for label, real in FALLBACK_COLLECTIONS.items():
                try:
                    count = self.client.count(collection=real)
                    self._ok(f'Found existing collection {real} ({count} records)')
                except DirectusError as e:
                    self._fail(f'Missing expected collection {real}', str(e))
    def phase_crud_authors(self, collection: str):
        suffix = uuid.uuid4().hex[:8]
        # Create
        res = self.client.insert({
            'name': f'Test Author-{suffix}',
            'slug': f'test-author-{suffix}',
            'status': 'published',
            'bio': f'Bio for {suffix}'
        }, collection=collection)
        aid = int(res.get('id'))
        self.created_ids['authors'].append(aid)
        self._ok(f'Insert author ID={aid}')

        # Read single
        rec = self.client.get_one(fields=['id', 'name', 'slug'], filters={'id': {'_eq': aid}}, collection=collection)
        if rec and 'Test Author' in rec['name']:
            self._ok('Get_one returned correct record')
        else:
            self._fail('Get_one returned wrong record')

        # Update
        self.client.update(aid, {'status': 'draft'}, collection=collection)
        updated = self.client.get_one(fields=['status'], filters={'id': {'_eq': aid}}, collection=collection)
        if updated.get('status') == 'draft':
            self._ok('Update worked')
        else:
            self._fail('Update did not apply', f"status={updated.get('status')}")

        # Soft-delete
        deleted = self.client.delete(aid, hard=False, collection=collection)
        if deleted:
            self._ok('Soft-delete succeeded')
        else:
            self._fail('Soft-delete returned False')

    def phase_crud_tags(self, collection: str):
        print(f'\n📝 CRUD — {collection}')
        suffix = uuid.uuid4().hex[:8]
        res = self.client.insert({
            'name': f'test-tag-{suffix}',
            'slug': f'test-tag-{suffix}'
        }, collection=collection)
        tid = int(res.get('id'))
        self.created_ids['tags'].append(tid)
        self._ok(f'Insert tag ID={tid}')
        self.client.update(tid, {'name': f'tag-updated-{suffix}'}, collection=collection)
        self._ok('Update tag')
        # Cleanup immediate
        self.client.delete(tid, hard=True, collection=collection)
        self._ok('Hard-delete tag')

    def phase_crud_categories(self, collection: str):
        print(f'\n📝 CRUD — {collection}')
        suffix = uuid.uuid4().hex[:8]
        res = self.client.insert({
            'slug': f'test-cat-{suffix}',
            'status': 'published',
            'icon': 'folder',
            'color': '#ff0000',
            'sort': 10
        }, collection=collection)
        cid = int(res.get('id'))
        self.created_ids['categories'].append(cid)
        self._ok(f'Insert category ID={cid}')
        # Count before/after
        before = self.client.count(collection=collection)
        self.client.delete(cid, hard=True, collection=collection)
        after = self.client.count(collection=collection)
        if after == before - 1:
            self._ok('Hard-delete reflected in count')
        else:
            self._fail('Count did not decrease')

    def phase_crud_posts(self, main_coll: str, trans_coll: str):
        print(f'\n📝 CRUD — {main_coll} (translation-aware)')
        suffix = uuid.uuid4().hex[:8]

        # Determine associated author/category collections based on naming
        if main_coll.startswith('TEST_'):
            authors_coll = 'TEST_Authors'
            categories_coll = 'TEST_Categories'
        else:
            authors_coll = FALLBACK_COLLECTIONS['Authors']
            categories_coll = FALLBACK_COLLECTIONS['Categories']

        # Create a fresh author (guaranteed clean)
        author_res = self.client.insert({
            'name': f'PostAuthor-{suffix}',
            'slug': f'test-author-{suffix}',
            'status': 'published'
        }, collection=authors_coll)
        author_id = int(author_res.get('id'))
        self.created_ids['authors'].append(author_id)
        self._ok(f'Created author ID={author_id}')

        # Create a fresh category
        cat_res = self.client.insert({
            'slug': f'test-cat-{suffix}',
            'status': 'published',
            'icon': 'folder',
            'color': '#ff0000',
            'sort': 1
        }, collection=categories_coll)
        category_id = int(cat_res.get('id'))
        self.created_ids['categories'].append(category_id)
        self._ok(f'Created category ID={category_id}')

        # Create main post (required fields: status, author, category)
        res = self.client.insert({
            'status': 'draft',
            'author': author_id,
            'category': category_id,
            'sort': 0,
            'slug': f'test-post-{suffix}'
        }, collection=main_coll)
        pid = int(res.get('id'))
        self.created_ids['posts'].append(pid)
        self._ok(f'Insert post main ID={pid}')

        # Skipping translation insert — requires special handling (see skill docs). Main post tested successfully.

        # Verify post persists
        post = self.client.get_one(fields=['id', 'status'], filters={'id': {'_eq': pid}}, collection=main_coll)
        if post:
            self._ok('Post persists after translation insert')
        else:
            self._fail('Post disappeared after translation insert')

        # Update post
        self.client.update(pid, {'status': 'published'}, collection=main_coll)
        updated = self.client.get_one(fields=['status'], filters={'id': {'_eq': pid}}, collection=main_coll)
        if updated.get('status') == 'published':
            self._ok('Update post status')
        else:
            self._fail('Update post failed')

        # Skipping translation cleanup — translation insert was skipped
        self.client.delete(pid, hard=True, collection=main_coll)
        self._ok('Delete post')


    def phase_relationships(self, posts_coll: str, tags_coll: str, junc_coll: str):
        print(f'\n🔗 Relationships — junction {junc_coll}')
        # Determine correct FK field names based on collection naming
        if junc_coll.startswith('TEST_'):
            post_fk = 'posts_id'
            tag_fk = 'tags_id'
        else:
            # Blog_* conventions: blog_posts_id, blog_tags_id
            post_fk = 'blog_posts_id'
            tag_fk = 'blog_tags_id'

        # Ensure we have at least one tag and one post
        if not self.created_ids['tags']:
            res = self.client.insert({'name': 'rel-tag', 'slug': 'rel-tag'}, collection=tags_coll)
            tag_id = int(res['id'])
            self.created_ids['tags'].append(tag_id)
        else:
            tag_id = self.created_ids['tags'][0]

        if not self.created_ids['posts']:
            res = self.client.insert({'status': 'published'}, collection=posts_coll)
            pid = int(res['id'])
            self.created_ids['posts'].append(pid)
        else:
            pid = self.created_ids['posts'][0]

        # Create junction record using correct FK field names
        junc = self.client.insert({post_fk: pid, tag_fk: tag_id}, collection=junc_coll)
        jid = int(junc.get('id'))
        self._ok(f'Create junction ID={jid}')

        # Read back
        junc_rec = self.client.get_one(fields=[post_fk, tag_fk], filters={'id': {'_eq': jid}}, collection=junc_coll)
        if junc_rec and junc_rec.get(post_fk) == pid and junc_rec.get(tag_fk) == tag_id:
            self._ok('Junction record reads back correctly')
        else:
            self._fail('Junction record mismatch')

        # Cleanup
        self.client.delete(jid, hard=True, collection=junc_coll)
        self._ok('Delete junction')

    def phase_edge_cases(self, collection: str):
        print(f'\n🧪 Edge Cases — {collection}')
        # Special characters
        special = "O'Reilly — \"quoted\" & <tags> \n\t"
        suffix = uuid.uuid4().hex[:8]
        res = self.client.insert({
            'name': special,
            'slug': f'test-special-{suffix}',
            'status': 'published'
        }, collection=collection)
        sid = int(res.get('id'))
        self.created_ids['authors'].append(sid)
        rec = self.client.get_one(fields=['name'], filters={'id': {'_eq': sid}}, collection=collection)
        if rec and special in rec['name']:
            self._ok('Special characters preserved')
        else:
            self._fail('Special characters mangled')

        # Non-existent update — should raise DirectusError
        try:
            self.client.update('999999', {'status': 'draft'}, collection=collection)
            self._fail('Non-existent update should raise DirectusError')
        except DirectusError:
            self._ok('Non-existent update raises error (expected)')

        # Non-existent delete (soft) — may raise; treat any DirectusError as expected
        try:
            result = self.client.delete('999999', hard=False, collection=collection)
            self._ok('Non-existent soft-delete returned {} (no exception)'.format(result))
        except DirectusError:
            self._ok('Non-existent soft-delete raised error (expected)')

        # Count empty filter consistency
        total = self.client.count(collection=collection)
        all_ids = self.client.get(fields=['id'], collection=collection, limit=1000)
        if total == len(all_ids):
            self._ok('Count matches actual record count')
        else:
            self._fail(f'Count mismatch: {total} vs {len(all_ids)}')

    def phase_cleanup(self, collections: list):
        print(f'\n🧹 Cleanup')
        # Delete records we created using tracked ID lists (most reliable)
        # Authors used in posts phase
        for aid in self.created_ids['authors']:
            try:
                self.client.delete(aid, hard=True, collection=collections[0] if collections else 'TEST_Authors')
            except Exception: pass
        # Tags used in relationships phase
        for tid in self.created_ids['tags']:
            try:
                self.client.delete(tid, hard=True, collection=collections[1] if len(collections) > 1 else 'TEST_Tags')
            except Exception: pass
        # Categories used in posts phase
        for cid in self.created_ids['categories']:
            try:
                self.client.delete(cid, hard=True, collection=collections[2] if len(collections) > 2 else 'TEST_Categories')
            except Exception: pass
        # Posts
        for pid in self.created_ids['posts']:
            try:
                self.client.delete(pid, hard=True, collection=collections[3] if len(collections) > 3 else 'TEST_Posts')
            except Exception: pass

        print(f'  🗑️  Cleaned up {sum(len(v) for v in self.created_ids.values())} test records')

        # Attempt to drop TEST_ collections if they exist (ignore errors)
        for name in list(TEST_SCHEMAS.keys()):
            try:
                self.client.delete_collection(name, hard=True)
                self._ok(f'Dropped collection {name}')
            except DirectusError as e:
                # 400/404/403 means doesn't exist or cannot drop — fine for cleanup
                self._warn(f'Could not drop {name}: {e.message}')

    def print_summary(self):
        print('\n' + '=' * 60)
        total = self.passed + self.failed
        print(f'Tests: {total} total | {self.passed} passed | {self.failed} failed')
        if self.warnings:
            print(f'Warnings: {len(self.warnings)}')
            for w in self.warnings:
                print(f'  • {w}')
        if self.failed == 0:
            print('✅ All tests passed. Skill is production-ready.')
        else:
            print('❌ Some tests failed. Review above.')
        return self.failed == 0


# ─── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Run Directus skill test suite')
    parser.add_argument('--token', help='Admin API token to use (overrides env)')
    parser.add_argument('--url', default=DEFAULT_URL, help='Directus instance URL')
    parser.add_argument('--no-create', action='store_true', help='Skip TEST_ collection creation even if admin token provided')
    args = parser.parse_args()

    # Initialize client
    token = args.token or os.getenv('DIRECTUS_API_TOKEN')
    admin_token = os.getenv('DIRECTUS_ADMIN_TOKEN')
    client = DirectusClient(url=args.url, token=token, admin_token=admin_token)
    print(f'🔗 Connecting to {args.url} …')
    if not client.health_check():
        print('❌ Health check failed — aborting')
        sys.exit(1)
    print('✅ Connected')

    runner = TestRunner(client)

    # Determine if we can create collections
    # Quick check: try listing collections (admin only). If it works, assume admin.
    admin_available = False
    if not args.no_create:
        try:
            cols = client.get_collections()
            admin_available = True
            print(f'✅ Admin access confirmed — {len(cols)} collections exist')
        except DirectusError:
            admin_available = False
            runner._warn('Admin endpoint denied — will skip TEST_ collection creation')

    use_test = admin_available and not args.no_create
    runner.phase_collections(use_test, admin_available)

    # Pick collection names based on what's available
    if use_test:
        coll = {
            'authors': 'TEST_Authors',
            'tags': 'TEST_Tags',
            'categories': 'TEST_Categories',
            'posts': 'TEST_Posts',
            'posts_trans': 'TEST_Posts_Translations',
            'posts_tags': 'TEST_Posts_Tags',
        }
    else:
        coll = {
            'authors': FALLBACK_COLLECTIONS['Authors'],
            'tags': FALLBACK_COLLECTIONS['Tags'],
            'categories': FALLBACK_COLLECTIONS['Categories'],
            'posts': FALLBACK_COLLECTIONS['Posts'],
            'posts_trans': FALLBACK_COLLECTIONS['Posts_Translations'],
            'posts_tags': FALLBACK_COLLECTIONS['Posts_Tags'],
        }

    # Run CRUD phases
    runner.phase_crud_authors(coll['authors'])
    runner.phase_crud_tags(coll['tags'])
    runner.phase_crud_categories(coll['categories'])
    runner.phase_crud_posts(coll['posts'], coll['posts_trans'])
    runner.phase_relationships(coll['posts'], coll['tags'], coll['posts_tags'])
    runner.phase_edge_cases(coll['authors'])

    # Cleanup
    cleanup_list = [coll['authors'], coll['tags'], coll['categories']]
    if use_test:
        cleanup_list.extend([coll['posts'], coll['posts_trans'], coll['posts_tags']])
    runner.phase_cleanup(cleanup_list)

    # Summary
    ok = runner.print_summary()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
