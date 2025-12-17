"""List compute instances in an OCI compartment.

This script queries the OCI Compute service and prints a concise
summary (name, state, OCID) or emits JSON suitable for ingestion
by other tools.

The implementation uses the OCI SDK and its pagination helper to
ensure all results are retrieved.
"""

from typing import Dict, List, Optional

import argparse
import json
import oci


VERSION = "listinstances.py version 17.12.2025"
COPY_RIGHT = "(c) Inge Os 2025"


def get_compute_instances_summary(oci_config: Dict, compartment_id: str) -> List[Dict]:
    """Return a list of simple summaries for compute instances.

    Each element in the returned list is a dict with keys: ``ocid``,
    ``name`` and ``state``.

    Args:
        oci_config: OCI configuration dict (from ``oci.config.from_file``).
        compartment_id: OCID of the compartment to query.

    Returns:
        A list of dictionaries describing the instances. On error an
        empty list is returned.
    """
    try:
        compute_client = oci.core.ComputeClient(oci_config)

        # Use SDK pagination helper to get all instances in the compartment
        response = oci.pagination.list_call_get_all_results(
            compute_client.list_instances, compartment_id=compartment_id
        )

        results = []
        for instance in response.data:
            results.append(
                {
                    "ocid": instance.id,
                    "name": instance.display_name,
                    "state": instance.lifecycle_state,
                }
            )

        return results

    except oci.exceptions.ServiceError as svc_err:
        print(f"OCI Service Error: {svc_err.code} - {svc_err.message}")
        return []
    except Exception as exc:  # pragma: no cover - runtime error path
        print(f"An unexpected error occurred: {exc}")
        return []

def main():
    """Main entry point: parse args, load config and perform requested action."""
    # Print program header
    print(VERSION)
    print(COPY_RIGHT)
    print()
    # CLI arguments
    args_parser = argparse.ArgumentParser(
        description=("List state of all compute instances in a compartment")
    )
    args_parser.add_argument(
        "--compartment-id", required=True, help="OCID of the compartment"
    )
    args_parser.add_argument(
        "--profile", required=True, help="OCI profile name from your config file"
    )
    args_parser.add_argument(
        "--configfile",
        required=False,
        default=None,
        help="Path to an alternate OCI config file (defaults to ~/.oci/config)",
    )

    args_parser.add_argument(
        "--json",
        required=False,
        action="store_true",
        help="Emit results as a single JSON array",
    )

    args = args_parser.parse_args()

    # Load OCI config (profile + optional config file)
    if args.configfile is None:
        oci_config = oci.config.from_file(profile_name=args.profile)
    else:
        oci_config = oci.config.from_file(
            file_location=args.configfile, profile_name=args.profile
        )

    # Fetch the list of instances
    instances = get_compute_instances_summary(oci_config, args.compartment_id)

    if not instances:
        print(f"No instances found in compartment {args.compartment_id}")
        return 0

    # Output as JSON array if requested
    if args.json:
        out = []
        for inst in instances:
            out.append(
                {
                    "instance": inst["name"],
                    "compartment_id": args.compartment_id,
                    "instance_id": inst["ocid"],
                    "profilename": args.profile,
                }
            )

        print(json.dumps(out, indent=2))
        return 0

    # Plain text output
    for inst in instances:
        print(f"Instance {inst['name']} state: {inst['state']} OCID: {inst['ocid']}")



if __name__ == '__main__':
    main()
    