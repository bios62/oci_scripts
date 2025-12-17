# listinstances.py

Lists compute instances in an OCI compartment and prints a concise summary.

This small utility queries the OCI Compute service and returns either a human-readable
summary (name, lifecycle state, OCID) or JSON objects suitable for inclusion in
other config files (for example the `startstop` scripts in this repo).

## Purpose

- Enumerate all compute instances in a compartment (handles API pagination).
- Produce either a plain text summary or JSON snippets (one object per instance).

## Prerequisites

- Python 3.6+
- OCI Python SDK: `pip install oci`
- Working OCI config/profile in `~/.oci/config` (or pass a custom config file)

## Location

- Script: `files/listinstances.py`
- Docs: `files/listinstances.md` (this file)

## Usage

```bash
python files/listinstances.py \
  --compartment-id ocid1.compartment.oc1..aaaaaaa... \
  --profile DEFAULT

# To emit JSON snippets suitable for merging into other scripts' config files:
python files/listinstances.py \
  --compartment-id ocid1.compartment.oc1..aaaaaaa... \
  --profile DEFAULT \
  --json
```

If your OCI configuration is stored in a non-default file, pass `--configfile /path/to/config` and the script will use that file and the given profile name.

## Command line arguments

- `--compartment-id` (required): OCID of the compartment to list instances for.
- `--profile` (required): OCI profile name (from your OCI config file) to use.
- `--configfile` (optional): Path to an alternate OCI config file.
- `--json` (optional): If provided, emits JSON objects (one per instance) instead of plain text. These objects contain the keys `instance`, `compartment_id`, `instance_id`, and `profilename`.

## Behavior and output

- The script calls the Compute service `list_instances` and follows pagination until all results are retrieved.
- For each instance it collects:
  - `ocid` — instance OCID
  - `name` — instance display name
  - `state` — lifecycle state (RUNNING, STOPPED, etc.)

Plain text output example:

```
Instance my-server-1 state: RUNNING OCID: ocid1.instance.oc1..aaaaaaa...
Instance my-server-2 state: STOPPED OCID: ocid1.instance.oc1..bbbbbbb...
```

JSON output example (one JSON object per instance; printed as separate JSON documents):

```json
{
  "instance": "my-server-1",
  "compartment_id": "ocid1.compartment.oc1..aaaaaaa...",
  "instance_id": "ocid1.instance.oc1..aaaaaaa...",
  "profilename": "DEFAULT"
}
```

Notes:
- When `--json` is supplied the script prints multiple JSON objects separated by commas (so they can be pasted into a larger JSON array if needed).
- If no instances are found the script prints a short message and exits.

## Error handling

- OCI service errors are caught and printed; the script returns an empty list on failure.
- Invalid/missing config or profile will raise an exception from the OCI SDK when attempting to load credentials — provide a valid `--profile` and/or `--configfile`.

## Implementation notes

- Function `get_compute_instances_summary(oci_config, compartment_id)` performs the API calls and returns a list of simple dictionaries.
- The script deliberately minimizes memory usage by only keeping a small list of summary dictionaries rather than the full SDK models.

## Suggested improvements

- Add `--output-file` to write JSON results directly to a file.
- Provide `--filter` options (by name pattern, lifecycle state).
- Add unit tests that mock the OCI client to verify pagination and error handling.

---

If you'd like, I can:
- Convert the JSON output into a single JSON array (instead of separate objects),
- Add the `--output-file` option and commit the change, or
- Add filtering and sorting options to the CLI.
