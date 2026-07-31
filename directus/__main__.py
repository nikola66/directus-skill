#!/usr/bin/env python3
"""
Directus CLI — universal CRUD operations for any collection.

Usage:
    python3 -m directus query --collection Blog_Authors --fields id name --limit 5
    python3 -m directus count --collection Leads
    python3 -m directus insert --collection Blog_Tags --data '{"name":"Tech","slug":"tech"}'
    python3 -m directus health-check
    python3 -m directus ping
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from directus.client import DirectusClient, DirectusError


def main():
    parser = argparse.ArgumentParser(description='Directus GraphQL Operations')
    parser.add_argument('--url', default=None, help='Directus instance URL')
    parser.add_argument('--token', default=None, help='API token (or set DIRECTUS_API_TOKEN)')

    sub = parser.add_subparsers(dest='cmd', required=True)

    # Query command
    q = sub.add_parser('query', help='Query any collection')
    q.add_argument('--collection', required=True)
    q.add_argument('--fields', default='id')
    q.add_argument('--filters', default=None)
    q.add_argument('--limit', type=int, default=10)
    q.add_argument('--offset', type=int, default=None)
    q.add_argument('--sort', default=None)

    # Count command
    c = sub.add_parser('count', help='Count records')
    c.add_argument('--collection', required=True)
    c.add_argument('--filters', default=None)

    # Insert command
    i = sub.add_parser('insert', help='Insert record')
    i.add_argument('--collection', required=True)
    i.add_argument('--data', default='{}', help='JSON data to insert')
    i.add_argument('--raw', action='store_true', help='Treat --data as raw JSON (no field mapping)')

    # Update command
    u = sub.add_parser('update', help='Update record')
    u.add_argument('--collection', required=True)
    u.add_argument('--id', required=True, help='Record ID to update')
    u.add_argument('--data', default='{}', help='JSON data to update')

    # Delete command
    d = sub.add_parser('delete', help='Delete record')
    d.add_argument('--collection', required=True)
    d.add_argument('--id', required=True, help='Record ID')
    d.add_argument('--hard', action='store_true', help='Hard delete (permanent)')
    d.add_argument('--soft-field', default=None,
                   help='Field used for soft-delete (default: auto-detect status/archived)')
    d.add_argument('--soft-value', default=None,
                   help='Value to set for soft-delete (default: "Removed" for status, true for archived)')

    # Health check
    h = sub.add_parser('health-check', help='Check Directus connectivity (authenticated)')

    # Ping
    p = sub.add_parser('ping', help='Public liveness check (/server/ping)')

    # List collections
    l = sub.add_parser('collections', help='List all collections')

    args = parser.parse_args()
    
    try:
        client = DirectusClient(url=args.url, token=args.token)

        if args.cmd == 'query':
            records = client.get(
                fields=args.fields.split(),
                limit=args.limit,
                offset=args.offset,
                filters=json.loads(args.filters) if args.filters else None,
                sort=args.sort.split(',') if args.sort else None,
                collection=args.collection
            )
            print(json.dumps(records, indent=2, default=str))

        elif args.cmd == 'count':
            total = client.count(
                filters=json.loads(args.filters) if args.filters else None,
                collection=args.collection
            )
            print(f"Total {args.collection}: {total}")

        elif args.cmd == 'insert':
            data = json.loads(args.data)
            result = client.insert(data, collection=args.collection)
            print(json.dumps(result, indent=2, default=str))

        elif args.cmd == 'update':
            data = json.loads(args.data)
            result = client.update(args.id, data, collection=args.collection)
            print(json.dumps(result, indent=2, default=str))

        elif args.cmd == 'delete':
            soft_value = None
            if args.soft_field and args.soft_value is None:
                parser.error('--soft-value is required when --soft-field is provided')
            if args.soft_value is not None:
                try:
                    soft_value = json.loads(args.soft_value)
                except Exception:
                    soft_value = args.soft_value
            result = client.delete(
                args.id,
                hard=args.hard,
                collection=args.collection,
                archive_field=args.soft_field,
                archive_value=soft_value,
            )
            print(f"Deleted: {result}")

        elif args.cmd == 'health-check':
            ok = client.health_check()
            print(f"Health check: {'OK' if ok else 'FAILED'}")
            sys.exit(0 if ok else 1)

        elif args.cmd == 'ping':
            ok = client.ping()
            print(f"Ping: {'OK' if ok else 'FAILED'}")
            sys.exit(0 if ok else 1)

        elif args.cmd == 'collections':
            cols = client.get_collections()
            print(json.dumps(cols, indent=2))

    except DirectusError as e:
        print(f"Error: {e.message}", file=sys.stderr)
        if e.details:
            print(json.dumps(e.details, indent=2), file=sys.stderr)
        sys.exit(1 if e.status_code else 2)


if __name__ == '__main__':
    main()
