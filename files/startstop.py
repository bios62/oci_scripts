import oci
import argparse
import time
import json

#. Globals
RETRY_COUNT = 5
START = 'start'
STOP = 'stop'
INSTANCE_NAME='instance_name'
COMPARTMENT_ID='compartment_id'
NSG_NAME='nsg_name'
OCI_CONFIG_FILE='oci_config_file_path'
PROFILE='profilename'
#SESSION_CONFIG='session_config'

parameter_list=[COMPARTMENT_ID,PROFILE]

def lookup_instance_ocid_by_name(config, compartment_ocid, instance_name):
    compute = oci.core.ComputeClient(config)
    response = oci.pagination.list_call_get_all_results(
        compute.list_instances, compartment_id=compartment_ocid
    )
    for instance in response.data:
        if instance.display_name == instance_name:
            return instance.id
    print(f"No instance named '{instance_name}' found in compartment {compartment_ocid}")
    return None

def lookup_nsg_ocid_by_name(config, compartment_ocid, nsg_name):
    network = oci.core.VirtualNetworkClient(config)
    response = oci.pagination.list_call_get_all_results(
        network.list_network_security_groups, compartment_id=compartment_ocid
    )
    for nsg in response.data:
        if nsg.display_name == nsg_name:
            return nsg.id
        
    print(f"No NSG named '{nsg_name}' found in compartment {compartment_ocid}")
    return None

def list_vnics_of_image(compartment_ocid, instance_ocid, oci_config):
    # Initialize the config and clients
  
    compute_client = oci.core.ComputeClient(oci_config)
    network_client = oci.core.VirtualNetworkClient(oci_config)

    # Fetch the instance details for display
    instance = compute_client.get_instance(instance_ocid).data
    
    # List all VNIC attachments for this instance
    vnic_attachments = oci.pagination.list_call_get_all_results(
        compute_client.list_vnic_attachments,
        compartment_id=compartment_ocid,
        instance_id=instance_ocid
    ).data
    return vnic_attachments

def change_vnic_nsg_association(config, vnic_ocid, nsg_ocid,add=True):
    """
    Removes the specified NSG from the NSG list associated with a given VNIC.

    :param config: OCI config dictionary (from oci.config.from_file)
    :param vnic_ocid: OCID of the VNIC to update
    :param nsg_ocid: OCID of the NSG to remove
    """
    network_client = oci.core.VirtualNetworkClient(config)

    # Get current VNIC state
    vnic = network_client.get_vnic(vnic_ocid).data
    # Check for operation, add or remove
    response = None
    if add :
        # Check if the nsg is in the list of the vnic
        if vnic_ocid not in vnic.nsg_ids:
            updated_nsgs = vnic.nsg_ids or []
            updated_nsgs.append(nsg_ocid)
            update_details = oci.core.models.UpdateVnicDetails(nsg_ids=updated_nsgs)
            response = network_client.update_vnic(vnic_ocid, update_details)
            vnic = network_client.get_vnic(vnic_ocid).data
        else:
            print(f"NSG {nsg_ocid} is already associated with VNIC {vnic_ocid}. No update needed.")
            return
    else:
        # Make a new list without the specified NSG OCID
        current_nsgs = vnic.nsg_ids or []
        updated_nsgs = [nsg for nsg in current_nsgs if nsg != nsg_ocid]

        if len(current_nsgs) == len(updated_nsgs):
            print(f"NSG {nsg_ocid} not associated with VNIC {vnic_ocid}. No update needed.")
            return

    # Prepare and send the update
    update_details = oci.core.models.UpdateVnicDetails(nsg_ids=updated_nsgs)
    response = network_client.update_vnic(vnic_ocid, update_details)
    # print(f"Updated VNIC {vnic_ocid}. NSG {nsg_ocid} updated.")

def start_stop_instance(oci_config, instance_id, action,compartment_id):
    """
    Start or stop an OCI compute instance and print its lifecycle state.

    :param oci_config: OCI config, from oci.config.from_file()
    :param instance_id: OCID of the instance to start/stop
    :param action: 'start' or 'stop'
    """
    compute = oci.core.ComputeClient(oci_config)
    # Determine which action to take
    if action == 'start':
        print(f"Starting instance {instance_id} in compartment {compartment_id}...")
        compute.instance_action(instance_id, 'START')
    elif action == 'stop':
        print(f"Stopping instance {instance_id} in compartment {compartment_id}...")
        compute.instance_action(instance_id, 'STOP')
    else:
        print("Error: action must be 'start' or 'stop'")
        return

    # It's typical to wait a bit for state change; poll until not "STARTING" or "STOPPING"
    print("Waiting for state change...")
    i=0
    while i < RETRY_COUNT:
        instance = compute.get_instance(instance_id).data
        print(f"  Current state: {instance.lifecycle_state}")
        if action == 'start' and instance.lifecycle_state == 'RUNNING':
            break
        if action == 'stop' and instance.lifecycle_state == 'STOPPED':
            break
        time.sleep(5)  # Wait before checking again

    print(f"Action complete. Instance {instance_id} lifecycle state: {instance.lifecycle_state}")
 
def main():
    #
    # Add arguments and pars teh arguments
    #
    args_parser = argparse.ArgumentParser(description='Starts or stopp computer image, and if NSG names is supplied add/removes the NSG')
    args_parser.add_argument('--config-file', required=False, default=None, help='path to instance config file')
    args_parser.add_argument('--action',default="Start", required= False, help="start|stop")
    args_parser.add_argument('--instance-name',required= True, help="Name of instance")
    args = args_parser.parse_args()
    file=open(args.config_file)
    config=json.loads(file.read())
    file.close()
  
    #
    # Process config
    #
    instance_name=args.instance_name
    action=args.action
    instance_config= None
    #
    #. Lookup the instance config
    
    for i in range(0,len(config)):
        print(config[i])
        if config[i][INSTANCE_NAME] == args.instance_name:
            instance_config=config[i]
            break;
    # Exit if not found
    if instance_config is None:
        print(f'Instance name {args.instance_name} not defined in config file {args.config_file}')
        return 1
    #
    # validate config parameters
    #

    for param in parameter_list:
        if param not in instance_config:
            print(f'{param} is not defined in config file {args.config_file}')
            print(param+':')
            print(instance_config)
            return 1
    compartment_id=instance_config[COMPARTMENT_ID]
    oci_config_file=None
    profile=instance_config[PROFILE]
    if OCI_CONFIG_FILE in instance_config:
        oci_config_file=instance_config[OCI_CONFIG_FILE]
    nsg_name=None
    if NSG_NAME in instance_config:
        nsg_name=instance_config[NSG_NAME]
    #
    # Allocate the config
    #  
    if oci_config_file is None:
        oci_config=  oci.config.from_file(profile_name=profile)
    else:
        oci_config=  oci.config.from_file(file_location=oci_config_file,profile_name=profile)
    # get OCID of instance
    instance_id=lookup_instance_ocid_by_name(oci_config,compartment_id,instance_name)
    if [nsg_name is not None]:
    # get OCID of nsg
        nsg_id=lookup_nsg_ocid_by_name(oci_config,compartment_id,nsg_name)
        if nsg_id is None:
            print("Nsg name provided but not found")
            return
    # Fist get list of all VNICS
    # If no VNICS exists, no NSG willø be added/removed
    if [nsg_name is not None]:
        vnics=list_vnics_of_image(
            compartment_ocid=compartment_id,
            instance_ocid=instance_id,
            oci_config=oci_config
        )
    
        if not vnics or len(vnics) == 0:
            print("No valid VNICS found")
            return 1
        vnic_id=vnics[0].vnic_id
    # Branch on action
    if action.lower() == "start":
        # Optionally add the NSG if --nsg flag is provided
        if nsg_name is not None:
            change_vnic_nsg_association(oci_config, vnic_id, nsg_id, add=True)
        start_stop_instance(oci_config, instance_id, START, compartment_id)
    elif action.lower() == "stop":
        start_stop_instance(oci_config, instance_id, STOP, compartment_id)
        # Optionally remove the NSG if --nsg flag is provided
        if nsg_name is not None:
            change_vnic_nsg_association(oci_config, vnic_id, nsg_id, add=False)
    else:
        args_parser.print_help()


if __name__ == '__main__':
    main()