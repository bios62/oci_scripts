## OCI Audit Log Streaming Utility

This repository contains a small utility (oci_audit_streamer.py) that efficiently fetches Oracle Cloud Infrastructure (OCI) Audit events for large time ranges. The script handles the OCI Audit API limitations (14-day max query window) by splitting long ranges into smaller chunks and streams events directly to disk as a single valid JSON array to keep memory usage low.

### Prerequisites

- Python 3.6+ (3.8+ recommended)
- OCI Python SDK
- A valid OCI config file (default: `~/.oci/config`) with the profile you want to use

Install the OCI SDK:

```bash
pip install oci
```

### Quick overview

- The script pages through the Audit API results and writes events incrementally to a single JSON file.
- If the requested date range is longer than 14 days, the script breaks it into 14-day (or smaller) chunks and queries each chunk sequentially.
- Within each chunk the script fetches all pages of events and streams them to disk to avoid large memory footprints.

### Usage

Run the script with the required arguments:

```bash
python oci_audit_streamer.py \
  --startdate 2024-01-01 \
  --enddate 2024-01-31 \
  --profilename DEFAULT \
  --outputfile jan_2024_audit.json \
  --eventfilter ocid1.compartment.oc1..aaaaaaaaxxxxxx
```

Replace the example Tenancy/Compartment OCID with your OCID.

#### Arguments

**Mandatory:**

- `--startdate` — Start date (inclusive). Format: `YYYY-MM-DD` (e.g. `2024-01-01`).
- `--enddate` — End date (inclusive). Format: `YYYY-MM-DD` (e.g. `2024-01-31`). The script treats the end date as the end of that day.
- `--profilename` — OCI profile name from your `~/.oci/config` (default profile commonly `DEFAULT`).
- `--outputfile` — Path to the output JSON file. The script writes a single valid JSON array containing all events.
- `--eventfilter` — The OCID of the compartment (often the tenancy/root compartment OCID) to query for Audit events.

** Relevant and typical IAM events to use as filter **

| Event Category        | Key Event Names (eventName)           | Description                                                                                    |
|-----------------------|----------------------------------------|-----------------------------------------------------------------------------------------------|
| Login Success/Failure | LoginSuccess                           | A user successfully logged into the OCI Console.                                              |
| Login Failure         | LoginFailure                           | An unsuccessful attempt to log into the OCI Console (e.g., wrong password, disabled account). |
| MFA Status Change     | UpdateUserMfaStatus                    | A user's Multi-Factor Authentication setting was enabled or disabled.                         |
| Auth Token Management | CreateAuthToken, DeleteAuthToken       | Creation or removal of tokens used by external tools/scripts.                                 |
| API Key Management    | CreateApiKey, DeleteApiKey             | Creation or removal of API signing keys for the CLI or SDK.                                   |
| Console Password      | UpdateUserPassword                     | A user's OCI Console password was changed.                                                    |
| Session Activity      | SessionStart, SessionTimeout           | Start and end of a console session.                                                           |
| User Locking          | LockUser                               | An account was explicitly locked by an administrator (or automatically due to policy).        |

  

**Optional:**

- `--ociconfig` — Path to a custom OCI config file. Defaults to `~/.oci/config`.

### How streaming works

The script is optimized for performance and low memory usage:

- Date chunking: If the total duration exceeds OCI's 14-day query window, the script splits the full range into sequential chunks (14 days or less) and queries them one after another.
- Pagination: For each chunk, the script uses the OCI SDK pagination helpers (or manual paging) so no events are missed.
- JSON streaming: Events are written to the output file incrementally:
  1. The script writes the opening `[` bracket.
 2. It iterates over events yielded by the query generator and writes each JSON object to disk, inserting commas as needed.
 3. After all chunks/pages are processed the script writes the closing `]` bracket.

This approach guarantees the output file is a valid JSON array while keeping peak memory usage low.

### Notes and tips

- If you need CSV output for analysis, pipe the JSON through a small script or use `pandas.json_normalize` to convert the events to tabular form.
- For long-running exports, run the script in a screen/tmux session or on a machine with stable network connectivity.
- Ensure your OCI user/profile has permissions to call the Audit service for the target compartment.

### Example: convert JSON to CSV (quick)

```python
import pandas as pd
import json

with open('jan_2024_audit.json') as f:
    data = json.load(f)

events = data if isinstance(data, list) else data.get('data', [])
df = pd.json_normalize(events)
df.to_csv('jan_2024_audit.csv', index=False)
```

### License

This tool is provided as-is. Add your preferred license file to the repository (for example, Apache-2.0).