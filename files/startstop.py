import argparse
import json
import time
from typing import Dict, List, Optional

import oci
from oci.util import to_dict


"""startstop.py

Utility to start/stop OCI compute instances and optionally add/remove
Network Security Groups (NSGs) on the instance primary VNIC.

This file is intentionally small and uses the OCI Python SDK.
"""

# Globals / constants
VERSION = "startstop.py version 16.12.2025"
COPY_RIGHT = "(c) Inge Os 2025"
RETRY_COUNT = 5
START = "start"
STOP = "stop"
STATUS = "status"

INSTANCE_NAME = "instance"
COMPARTMENT_ID = "compartment_id"
NSG_NAME = "nsg_name"
OCI_CONFIG_FILE = "oci_config_file_path"
PROFILE = "profilename"
TENANCY = "tenancy"

# Required parameters inside the per-instance config entries
parameter_list = [COMPARTMENT_ID, PROFILE]

def lookup_instance_ocid_by_name(
    config: Dict, compartment_ocid: str, instance_name: str
) -> Optional[str]:
    """Return the OCID for an instance by its display name.

    Args:
        config: OCI configuration mapping (from ``oci.config.from_file``).
        compartment_ocid: OCID of the compartment to search in.
        instance_name: Display name of the instance to find.

    Returns:
        The instance OCID as a string if found; otherwise ``None``.
    """
    compute_client = oci.core.ComputeClient(config)

    response = oci.pagination.list_call_get_all_results(
        compute_client.list_instances, compartment_id=compartment_ocid
    )

    for instance in response.data:
        if instance.display_name == instance_name:
            return instance.id

    print(
        f"No instance named '{instance_name}' found in compartment {compartment_ocid}"
    )
    return None

def lookup_nsg_ocid_by_name(
    config: Dict, compartment_ocid: str, nsg_name: str
) -> Optional[str]:
    """Return the OCID of a Network Security Group (NSG) by display name.

    Args:
        config: OCI configuration mapping.
        compartment_ocid: OCID of the compartment to search in.
        nsg_name: Display name of the NSG to find.

    Returns:
        The NSG OCID if found; otherwise ``None``.
    """
    network = oci.core.VirtualNetworkClient(config)
    response = oci.pagination.list_call_get_all_results(
        network.list_network_security_groups, compartment_id=compartment_ocid
    )

    for nsg in response.data:
        if nsg.display_name == nsg_name:
            return nsg.id

    print(f"No NSG named '{nsg_name}' found in compartment {compartment_ocid}")
    return None

def list_vnics_of_image(
    compartment_ocid: str, instance_ocid: str, oci_config: Dict
) -> List:
    """Return the VNIC attachment list for the given instance.

    The returned value is the raw list of SDK model objects representing
    VNIC attachments.
    """
    compute_client = oci.core.ComputeClient(oci_config)
    network_client = oci.core.VirtualNetworkClient(oci_config)

    # Fetch instance details (kept for potential future use)
    _ = compute_client.get_instance(instance_ocid).data

    # List all VNIC attachments for this instance (use pagination helper)
    vnic_attachments = (
        oci.pagination.list_call_get_all_results(
            compute_client.list_vnic_attachments,
            compartment_id=compartment_ocid,
            instance_id=instance_ocid,
        )
        .data
    )

    return vnic_attachments

def change_vnic_nsg_association(
    config: Dict, vnic_ocid: str, nsg_ocid: str, add: bool = True
) -> None:
    """Add or remove an NSG OCID from a VNIC's NSG list.

    Args:
        config: OCI SDK configuration mapping.
        vnic_ocid: OCID of the VNIC to update.
        nsg_ocid: OCID of the NSG to add or remove.
        add: If True add the NSG; if False remove it.
    """
    network_client = oci.core.VirtualNetworkClient(config)

    # Get current VNIC state
    vnic = network_client.get_vnic(vnic_ocid).data

    if add:
        current_nsgs = vnic.nsg_ids or []
        if nsg_ocid in current_nsgs:
            print(
                f"NSG {nsg_ocid} is already associated with VNIC {vnic_ocid}."
                " No update needed."
            )
            return

        updated_nsgs = current_nsgs + [nsg_ocid]
    else:
        current_nsgs = vnic.nsg_ids or []
        updated_nsgs = [n for n in current_nsgs if n != nsg_ocid]

        if len(current_nsgs) == len(updated_nsgs):
            print(
                f"NSG {nsg_ocid} not associated with VNIC {vnic_ocid}."
                " No update needed."
            )
            return

    # Prepare and send the update
    update_details = oci.core.models.UpdateVnicDetails(nsg_ids=updated_nsgs)
    network_client.update_vnic(vnic_ocid, update_details)

def start_stop_instance(
    oci_config: Dict, instance_id: str, action: str, compartment_id: str
) -> None:
    """
    Start or stop an OCI compute instance and print its lifecycle state.

    :param oci_config: OCI config, from oci.config.from_file()
    :param instance_id: OCID of the instance to start/stop
    :param action: 'start', 'stop'
    """
    compute = oci.core.ComputeClient(oci_config)
    # Determine which action to take
    if action == 'start':
        print(f"Starting instance {instance_id} in compartment {compartment_id}...")
        compute.instance_action(instance_id, 'START')
    elif action == 'stop':
        print(f"Stopping instance {instance_id} in compartment {compartment_id}...")
        compute.instance_action(instance_id, 'STOP')
    elif action == 'status':
        print(f"Status of instance {instance_id} \nin compartment {compartment_id}...")
        instance_status=compute.get_instance(instance_id)
        print(f'{instance_status.data.display_name}: {instance_status.data.lifecycle_state}')
        return
    else:
        print("Error: action must be 'start', 'stop' or 'status")
        return

    # It's typical to wait a bit for state change; poll until not "STARTING" or "STOPPING"
    print("Waiting for state change...")
    i = 0
    while i < RETRY_COUNT:
        instance = compute.get_instance(instance_id).data
        print(f"  Current state: {instance.lifecycle_state}")
        if action == 'start' and instance.lifecycle_state == 'RUNNING':
            break
        if action == 'stop' and instance.lifecycle_state == 'STOPPED':
            break
        time.sleep(5)  # Wait before checking again
        i += 1

    print(f"Action complete. Instance {instance_id} lifecycle state: {instance.lifecycle_state}")
 
def main():
    """Main entry point: parse args, load config and perform requested action."""
    # Print program header
    print(VERSION)
    print(COPY_RIGHT)
    print()

    # CLI arguments
    args_parser = argparse.ArgumentParser(
        description=(
            "Start/stop a compute instance and optionally add/remove "
            "an NSG on the primary VNIC"
        )
    )

    args_parser.add_argument(
        "--config-file",
        required=True,
        default=None,
        help="path to instance config file",
    )
    args_parser.add_argument(
        "--action", default="Start", required=False, help="start|stop|status"
    )
    args_parser.add_argument(
        "--instance", required=False, help="Name of instance"
    )
    args_parser.add_argument(
        "--list",
        required=False,
        action="store_true",
        help="List instance names from config file",
    )

    args = args_parser.parse_args()

    # Open and parse the config JSON file
    try:
        with open(args.config_file) as fh:
            config = json.load(fh)
    except Exception as exc:
        print(f"Failed to open/parse config file: {exc}")
        return 1

    # If list flag is set, enumerate instance names and exit
    if args.list:
        print("Instances in config file")
        for entry in config:
            print(entry.get(INSTANCE_NAME))
        return 0

    # Determine requested instance and action
    instance_name = args.instance
    action = args.action
    instance_config = None

    # Lookup the instance config entry by name
    for entry in config:
        # show entry for debugging
        # print(entry)
        if entry.get(INSTANCE_NAME) == instance_name:
            instance_config = entry
            break

    if instance_config is None:
        print(f"Instance name {instance_name} not defined in config file {args.config_file}")
        return 1

    # Validate presence of mandatory parameters in the instance config
    for param in parameter_list:
        if param not in instance_config:
            print(f"{param} is not defined in config file {args.config_file}")
            print(param + ":")
            print(instance_config)
            return 1

    # Fetch OCI profile and optional config location
    oci_config_file = None
    profile = instance_config[PROFILE]
    if OCI_CONFIG_FILE in instance_config:
        oci_config_file = instance_config[OCI_CONFIG_FILE]

    # Optional NSG name in the instance config
    nsg_name = instance_config.get(NSG_NAME)

    # Load OCI config
    if oci_config_file is None:
        oci_config = oci.config.from_file(profile_name=profile)
    else:
        oci_config = oci.config.from_file(
            file_location=oci_config_file, profile_name=profile
        )

    # Use tenancy as compartment root for looking up instance
    #compartment_id = oci_config.get(TENANCY)
    compartment_id=instance_config[COMPARTMENT_ID]

    # Lookup instance OCID
    instance_id = lookup_instance_ocid_by_name(
        oci_config, compartment_id, instance_name
    )

    # If an NSG is specified, resolve NSG OCID and primary VNIC
    vnic_id = None
    nsg_id = None
    if nsg_name is not None:
        nsg_id = lookup_nsg_ocid_by_name(oci_config, compartment_id, nsg_name)
        if nsg_id is None:
            print("NSG name provided but not found")
            return 1

        # Fetch VNIC attachments for the instance
        vnics = list_vnics_of_image(
            compartment_ocid=compartment_id,
            instance_ocid=instance_id,
            oci_config=oci_config,
        )

        if not vnics:
            print("No valid VNICs found")
            return 1

        vnic_id = vnics[0].vnic_id

    # Execute requested action
    if action.lower() == "start":
        if nsg_name is not None:
            change_vnic_nsg_association(oci_config, vnic_id, nsg_id, add=True)

        start_stop_instance(oci_config, instance_id, START, compartment_id)

    elif action.lower() == "stop":
        start_stop_instance(oci_config, instance_id, STOP, compartment_id)

        if nsg_name is not None:
            change_vnic_nsg_association(oci_config, vnic_id, nsg_id, add=False)

    elif action.lower() == "status":
        # Status currently reuses start_stop_instance which prints lifecycle state
        start_stop_instance(oci_config, instance_id, STATUS, compartment_id)

    else:
        print("Action must be start|stop|status")
        args_parser.print_help()


if __name__ == '__main__':
    main()
    