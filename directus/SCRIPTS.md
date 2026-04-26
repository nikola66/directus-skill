# Directus Skill Utilities

Reusable maintenance scripts powered by `skills.directus.client.DirectusClient`.

## Important Note

The Directus skill is now **collection-agnostic**. All scripts below default to the `Leads` collection for backward compatibility, but you can modify them to work with any collection by passing `collection='Your_Collection'` to client methods.

## Tools

| Script | Purpose | When to run |
|--------|---------|-------------|
| `tools/patch_missing_directus.py` | Sync email log → Directus (inserts records missing from CRM) | After manual sends outside daily runner, or if Directus gets out of sync |
| `tools/dedupe_directus.py` | Merge duplicate leads by email (keeps newest, soft-deletes old) | When duplicates detected (e.g. same email with different domains) |
| `tools/manual_prospect.py` | Send one-off email + auto-log to Directus | For LinkedIn/manual outreach, ad-hoc prospects |
| `tools/update_delivery_status.py` | Pull Brevo events and update Directus status | Daily, ~3 hours after send (already in cron) |

## Usage Examples

### Patch missing records (sync from email log)
```bash
python3 tools/patch_missing_directus.py
```

### Merge duplicates
```bash
python3 tools/dedupe_directus.py
```

### Manual one-off send
```bash
python3 tools/manual_prospect.py \
  jane@example.com \
  "Jane" \
  "Example Corp" \
  example.com \
  "Head of IT" \
  "https://ainex.aratech.ae/shared-report?token=***" \
  "linkedin"
```

### Check Directus health
```bash
python3 -m skills.directus health-check
# or
python3 -m skills.directus query --limit 5
```

### Using a different collection
```python
from skills.directus.client import DirectusClient

client = DirectusClient()
# Insert into a custom collection
client.insert({'name': 'Test', 'slug': 'test'}, collection='Custom_Collection')
```

## Notes

- All tools use `skills.directus.client.DirectusClient` singleton (shared config via env)
- Soft-delete is default — never hard-delete unless absolutely certain
- Email addresses are the unique key (case-insensitive) for Lead-specific scripts
- Status values containing "Contacted" mark a lead as already reached — dedup logic respects this
- To adapt these scripts for other schemas, update the `collection` parameter and field names accordingly
