**Logstreamer** — OCI Audit streaming utility

- **Purpose**: Stream OCI Audit events for a given date range into a single, valid JSON array. The script splits large ranges into smaller chunks (up to 7 days per chunk by default) and paginates through the Audit API to avoid memory or API limits.

- **File**: [files/logstreamer.py](files/logstreamer.py)

**Dependencies**
- Python 3.8+
- `oci` Python SDK (install with `pip install oci`)

**Quick overview**
- The main implementation is in the `OciAuditStreamer` class which:
  - loads OCI config and initializes an `AuditClient`
  - breaks the requested date range into safe chunks
  - uses `oci.pagination.list_call_get_all_results` to iterate audit events
- The `stream_to_json_file()` utility writes streamed events to disk as a single JSON array and optionally filters events by a regex pattern.

**Command-line usage**

Basic invocation:

```bash
python files/logstreamer.py --startdate 01.12.25 --enddate 07.12.25 \
  --profilename DEFAULT --outputfile audit_logs.json
```

Arguments
- `--startdate` (required): Start date in `DD.MM.YY` format (example: `01.12.25`).
- `--enddate` (required): End date in `DD.MM.YY` format (query includes the full end day).
- `--profilename` (required): OCI config profile name to use (from `~/.oci/config`).
- `--outputfile` (required): Path to the output JSON file to create.
- `--eventfilter` (optional): A semicolon-separated list of regular expressions to match against `event_type` in the audit event payload. Only matching events will be written.
- `--ociconfig` (optional): Path to an alternative OCI config file (defaults to `~/.oci/config`).

Notes about `--eventfilter`
- Provide one or more regular expressions separated by `;` (semicolon). The script checks `jitem['data']['event_type']` against each regex and writes the event if any match.

Examples
- Stream all audit events for a week:

```bash
python files/logstreamer.py --startdate 01.12.25 --enddate 07.12.25 \
  --profilename DEFAULT --outputfile /tmp/audit_week.json
```

- Stream only events where the event type contains `Instance` or `Compute` (example filter):

```bash
python files/logstreamer.py --startdate 01.12.25 --enddate 07.12.25 \
  --profilename DEFAULT --outputfile /tmp/audit_compute.json \
  --eventfilter "Instance|Compute"
```

Output
- The script writes a single JSON array to the specified `--outputfile`. It also writes a small `allevents.json` file in the current working directory containing a simple event name frequency map (internal diagnostic).

Behavior and implementation details
- Date parsing requires `DD.MM.YY` format. An invalid date will exit with an error message.
- The script uses UTC midnight for day boundaries and includes the full end day (end-of-day inclusive).
- The `OciAuditStreamer` breaks the range into chunks sized by `MAX_CHUNK_DAYS` to avoid hitting API time-range constraints (default constant in the file).
- The script uses the OCI SDK pagination helper `list_call_get_all_results` to transparently iterate pages.

Error handling
- If the `oci` package is not installed the script exits with a helpful message.
- Service errors from the Audit API are printed for the affected chunk and the script continues to the next chunk.

Best practices and tips
- For large ranges prefer running the script during off-peak hours and ensure your OCI profile has access to the tenancy/compartment.
- If you want to restrict to a compartment, use the profile/tenancy configured in your OCI config file; the script currently uses `tenancy` from the loaded config as the compartment root.
- After streaming, you can post-process the output JSON with `jq` or load it into pandas with `pandas.json_normalize`.

Possible improvements
- Add a `--compartment` argument to explicitly specify compartment OCID instead of using the tenancy field.
- Add an option to gzip the output stream to save disk space for very large exports.
- Add unit tests that mock the OCI client and pagination helper.

If you want, I can also:
- run a quick linter/formatter pass on `files/logstreamer.py` and add the file to the repo README,
- or add a small example `curl`/`jq` snippet showing how to count event types from the output.
