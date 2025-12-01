# oci_scripts

A small collection of Oracle Cloud Infrastructure (OCI) helper scripts used for common operational tasks: creating Bastion sessions, listing resources across compartments, exporting audit/log events to CSV, and starting/stopping compute instances (with optional NSG association changes).

This repository is intended as a practical toolbox of scripts; each script is standalone and typically relies on either the OCI Python SDK (`oci`) or the OCI CLI.

Prerequisites
-------------
- Python 3.8+
- OCI Python SDK: `pip install oci`
- `jq` (for the bash wrapper `startstop.bash`)
- OCI CLI (for some bash-based helpers)
- An OCI config file at the default location (`~/.oci/config`) or supplied via script arguments

Top-level files
----------------
- `startstop.py` (root) — convenience script to start/stop instances (may be a wrapper/alternate version of the Python start/stop utility in `files/`).
- `traverse_compartments.py` — helper to recurse compartments and call resource-specific functions (alternate resource enumeration helper).

Files directory
---------------
Below are the files found in the `files/` directory with a short description for each and their intended usage.

- `bastionsession.py`
  - Purpose: Full-featured Bastion service manager implemented with the OCI Python SDK.
  - Key features:
    - Create and manage Bastion sessions (managed SSH or port-forwarding).
    - Generate client-side and server-side commands for connecting through the Bastion (SSH or PuTTY variants).
    - Optionally fork a shell and run the generated SSH/tunnel commands, wait for session expiry and recreate sessions.
    - Validates and populates configuration values, supports TTL and session polling until ACTIVE.
  - Usage: Run the script with a JSON bastion config and a `--session` name; use `--exec` to actually execute the generated SSH commands.
  - Notes: The script contains robust config validation utilities (`get_validated_config_entry`, `valdate_config`) and handles async execution for session-driven flows.

- `listresources.py`
  - Purpose: Resource extraction and reporting across compartments.
  - Key features:
    - Recursive compartment traversal with optional resource-specific list functions.
    - Can list: compartments, compute instances, compute instances with agent status, policies, block storage, and unattached volumes.
    - Provides helper functions for agent/plugin status reporting (`list_oci_agent_status`) and subscribed regions discovery.
  - Usage: `python listresources.py --resource compute --profile DEFAULT --configfile ~/.oci/config` (see script `--help` for details).
  - Notes: Intended as an operational helper to gather inventory and detect missing agents (e.g., vulnerability scanning agent) on running instances.

- `logeventstocsv.py`
  - Purpose: Convert JSON event export (for example Audit events) into a CSV using `pandas` for quick analysis.
  - Behavior: Reads JSON from an input file, normalizes with `pandas.json_normalize`, and writes a CSV.
  - Usage: `python logeventstocsv.py input.json output.csv`.
  - Notes: Assumes input JSON is either an array of events or contains a top-level `data` key with events.

- `script2.py`
  - Purpose: Another resource traversal and utility module similar to `traverse_compartments.py` and `listresources.py`.
  - Key features:
    - Implements `recurseCompartments`, `listCompute`, `listPolicies`, `listBlockStorageInfo`, etc.
    - Provides `getConfig` helper to load OCI config and a `main()` CLI that wires resource selection and recursion.
  - Usage: `python script2.py --resource compute --compartment-id <OCID> --profile DEFAULT`.
  - Notes: This appears to be a slightly different/refactored take on the resource-listing utilities — useful if you want a smaller dependency footprint or alternate output formatting.

- `startstop.bash`
  - Purpose: Shell wrapper that uses `jq` and the OCI CLI to start/stop instances using a JSON file that maps instance display names to OCIDs and profile info.
  - Behavior: Extracts `compartment_id`, `profile`, and `instance_id` from a JSON file using `jq`, then calls the OCI CLI to start/stop the instance.
  - Usage: `./startstop.bash instances.json MyInstance start` (requires `jq` and OCI CLI configured).
  - Notes: Good for quick shell-based automation without needing to run Python; the Python variant exists in `files/startstop.py`.

- `startstop.py` (in `files/`)
  - Purpose: Python script to start/stop compute instances and optionally add/remove a Network Security Group (NSG) association on the instance's VNIC(s).
  - Key features:
    - Reads a JSON config (file format expected by the script) mapping instance names to compartments and profiles.
    - Looks up instance OCID by display name and can optionally look up NSG OCID by name.
    - Finds the primary VNIC, and can add or remove an NSG from the VNIC's `nsg_ids` (uses `update_vnic`).
    - Starts or stops the instance and polls for lifecycle state changes.
  - Usage: `python startstop.py --config-file instances.json --instance-name MyInstance --action start`
  - Notes: This script is more feature-rich than the bash wrapper and relies on the `oci` Python SDK; ensure credentials/config are available.

Contributing
------------
Contributions welcome — open a PR or copy/modify scripts for your environment. When contributing, please:

- Add unit tests where appropriate.
- Ensure any new dependencies are added to a `requirements.txt` or `pyproject.toml`.
- Include example config snippets for JSON files used by the scripts.

.gitignore
-----------
A reasonable `.gitignore` is included in the project to ignore typical Python artifacts (virtualenvs, __pycache__, logs, editor files, etc.).

Security and safety notes
-------------------------
- These scripts perform operations that can change the state of cloud resources (start/stop instances, change NSG associations, create bastion sessions). Run them with care and preferably against non-production/test tenancy when experimenting.
- Ensure that any private keys or sensitive credentials are kept out of the repository (use environment variables or secure secrets stores), and that config files containing secrets are added to `.gitignore`.

Files modified/created
----------------------
- `README.md` — this file (created)
- `.gitignore` — added to ignore common Python artifacts

If you want I can also:
- Initialize a local git repo here (run `git init`, create an initial commit) — I won't do that without your permission.
- Add example config JSON files or small integration tests that exercise the key flows (bastion creation, start/stop). 

