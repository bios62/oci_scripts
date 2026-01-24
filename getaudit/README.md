# OCI Audit Log Exporter

A small CLI utility to export Oracle Cloud Infrastructure (OCI) Audit events to a single JSON file. It pages through the Audit service, writes events incrementally to disk (to avoid large memory usage), and supports optional filtering by event (API operation) name.

This README is generated from the docstrings and comments in the original script `getaudit.py`.

## Features

- Streamed export of OCI Audit events with pagination.
- Incremental JSON writing (writes events as they are fetched to keep memory usage low).
- Optional filtering by event type (API operation name), e.g., `DeleteInstance`.
- Uses OCI SDK `oci` Python package.

## Requirements

- Python 3.8+
- OCI Python SDK

Install dependencies:

```bash
pip install -r requirements.txt
```

(Or install the OCI SDK directly: `pip install oci`.)

## Usage

The script is provided as `getaudit.py` and exposes a simple CLI:

```bash
python getaudit.py --start-date 2025-11-01T00:00:00Z \
    --end-date 2025-11-08T23:59:59Z \
    [--compartment-id ocid1.compartment.oc1..aaaaaaa...] \
    [--profile DEFAULT] \
    [--limit 50] \
    [--event-type DeleteInstance] \
    [--output-file audit_output.json]
```

Arguments:

- `--start-date` (required) — Start date/time in RFC 3339 format (e.g., `2025-11-01T00:00:00Z`).
- `--end-date` (required) — End date/time in RFC 3339 format (e.g., `2025-11-08T23:59:59Z`).
- `--compartment-id` (optional) — OCID of the compartment to query. If omitted, the tenancy OCID from the OCI config profile is used.
- `--profile` — OCI config profile name from `~/.oci/config` (default: `DEFAULT`).
- `--limit` — Page size (max 1000, default 50).
- `--event-type` — Optional API operation name to filter events by (e.g., `DeleteInstance`).
- `--output-file` — Output JSON filename (default: `audit_events_export.json`).

Output:
- A JSON array saved to the specified output file containing the exported Audit events.

## OCI Configuration

The script relies on the OCI config file (`~/.oci/config`) and the selected profile. Make sure your config is present and the profile contains the `tenancy` OCID if you don't specify `--compartment-id`.

## Error handling

- Service errors from the OCI SDK are caught and printed with the service error code and message.
- All other exceptions are caught and printed to help with debugging.

## Example

Export all `DeleteInstance` events during a week for a tenancy using the `DEFAULT` profile:

```bash
python getaudit.py --start-date 2025-11-01T00:00:00Z --end-date 2025-11-08T23:59:59Z --event-type DeleteInstance --output-file delete_events.json
```

## Development / Packaging

- A `requirements.txt` file is provided with the primary dependency (`oci`).
- Add unit tests or a small integration test by creating a synthetic or small time-window export.

## License

This project is licensed under the Apache License 2.0 — see the `LICENSE` file for details.
