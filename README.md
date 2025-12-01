# OCI Assets

This is my collection of scripts and assets made over time to make my life easier.
The assets are published as is. I have a smaller collection of writeups, pythonscripts and bash scripts 

A small collection of Oracle Cloud Infrastructure (OCI) helper scripts used for common operational tasks: creating Bastion sessions, listing resources across compartments, exporting audit/log events to CSV, extract audit log to file, tech brief on OPC user lockdown and starting/stopping compute instances (with optional NSG association changes).


This repository is intended as a practical toolbox of scripts; each script is standalone and typically relies on either the OCI Python SDK (`oci`) or the OCI CLI.

Prerequisites
-------------
- Python 3.8+
- OCI Python SDK: `pip install oci`
- `jq` (for the bash wrapper `startstop.bash`)
- OCI CLI (for some bash-based helpers)
- An OCI config file at the default location (`~/.oci/config`) or supplied via script arguments


Files directory
---------------
Below are the files found in the `files/` directory with a short description for each and their intended usage.


- `securing_exacs_or_dbcs_with_bastion_service_1.2.pdf`. [File](files/securing_exacs_or_dbcs_with_bastion_service_1.2.pdf)
  - The documnet discuss lockdown of the OPC userr for ExaCS and DBaaS for Oracle OCI.
  - The main idea is to utilize the OCi Bastion service to gain full control of OS access.

  -  Please view [securing exacs or dbcs with bastion service](securing_exacs_or_dbcs_with_bastion_service_1.2.pdf)
    

- `logstreamer.py` [File](files/logstreamer.py)

[logstreamer README](AUDIT_LOG_STREAMING.md)


- `bastionsession.py` [File](files/bastionsession.py)
  - Purpose: Full-featured Bastion service manager implemented with the OCI Python SDK.
  - Key features:
    - Create and manage Bastion sessions (managed SSH or port-forwarding).
    - Generate client-side and server-side commands for connecting through the Bastion (SSH or PuTTY variants).
    - Optionally fork a shell and run the generated SSH/tunnel commands, wait for session expiry and recreate sessions.
    - Validates and populates configuration values, supports TTL and session polling until ACTIVE.

For details view [BASTION.md](BASTION.md)
The script is located at [Oracle Technology Engineering](https://github.com/oracle-devrel/technology-engineering/tree/main/security/security-design/shared-assets/bastion-py-script) git repo

- `listresources.py` [File](files/listresources.py)
  - Purpose: Resource extraction and reporting across compartments.
  - Key features:
    - Recursive compartment traversal with optional resource-specific list functions.
    - Can list: compartments, compute instances, compute instances with agent status, policies, block storage, and unattached volumes.
    - Provides helper functions for agent/plugin status reporting (`list_oci_agent_status`) and subscribed regions discovery.
  - Usage: `python listresources.py --resource compute --profile DEFAULT --configfile ~/.oci/config` (see script `--help` for details).
  - Notes: Intended as an operational helper to gather inventory and detect missing agents (e.g., vulnerability scanning agent) on running instances.

- `logeventstocsv.py` [File](files/logeventstocsv.py)
  - Purpose: Convert JSON event export (for example Audit events) into a CSV using `pandas` for quick analysis.
  - Behavior: Reads JSON from an input file, normalizes with `pandas.json_normalize`, and writes a CSV.
  - Usage: `python logeventstocsv.py input.json output.csv`.
  - Notes: Assumes input JSON is either an array of events or contains a top-level `data` key with events.

- `listresources_recursive.py` [File](files/listresources_recursive.py)
  - Purpose: Another resource traversal and utility module similar to `traverse_compartments.py` and `listresources.py`.
  - Key features:
    - Implements `recurseCompartments`, `listCompute`, `listPolicies`, `listBlockStorageInfo`, etc.
    - Provides `getConfig` helper to load OCI config and a `main()` CLI that wires resource selection and recursion.
  - Usage: `python script2.py --resource compute --compartment-id <OCID> --profile DEFAULT`.
  - Notes: This appears to be a slightly different/refactored take on the resource-listing utilities — useful if you want a smaller dependency footprint or alternate output formatting. The main purpose of this script is to recursion over loop. Not it is slower (Python reccursion is slow...)


- `startstop.py`  [File](files/)
  - Purpose: Python script to start/stop compute instances and optionally add/remove a Network Security Group (NSG) association on the instance's VNIC(s).
  - Key features:
    - Reads a JSON config (file format expected by the script) mapping instance names to compartments and profiles.
    - Looks up instance OCID by display name and can optionally look up NSG OCID by name.
    - Finds the primary VNIC, and can add or remove an NSG from the VNIC's `nsg_ids` (uses `update_vnic`).
    - Starts or stops the instance and polls for lifecycle state changes.
  - Usage: `python startstop.py --config-file instances.json --instance-name MyInstance --action start`
  - Notes: This script is more feature-rich than the bash wrapper and relies on the `oci` Python SDK; ensure credentials/config are available.

- `startstop.bash` [File](files/)
  - Purpose: Shell wrapper that uses `jq` and the OCI CLI to start/stop instances using a JSON file that maps instance display names to OCIDs and profile info.
  - Behavior: Extracts `compartment_id`, `profile`, and `instance_id` from a JSON file using `jq`, then calls the OCI CLI to start/stop the instance.
  - Usage: `./startstop.bash instances.json MyInstance start` (requires `jq` and OCI CLI configured).
  - Notes: Good for quick shell-based automation without needing to run Python; the Python variant exists in `files/startstop.py`.
    
  - `traverse_compartments.py`  [File](files/)
    — helper to recurse compartments and call resource-specific functions (alternate resource enumeration helper).
    

# License

Copyright (c) 2025 Oracle and/or its affiliates.


Licensed under the Universal Permissive License (UPL), Version 1.0