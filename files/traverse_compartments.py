import oci
import os
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_compartment_tree(config, compartment_id, all_compartments=None):
    """
    Recursively fetches all compartments within a given compartment and its sub-compartments.
    
    Args:
        config (dict): OCI SDK configuration dictionary.
        compartment_id (str): The OCID of the parent compartment to start the traversal from.
        all_compartments (list, optional): A list to store all discovered compartments.
                                          Defaults to None, and a new list is created.
    
    Returns:
        list: A flat list of dictionaries, where each dictionary represents a compartment
              with its name and OCID.
    """
    if all_compartments is None:
        all_compartments = []

    identity_client = oci.identity.IdentityClient(config)
    
    # List all compartments within the specified parent compartment
    try:
        list_compartments_response = identity_client.list_compartments(
            compartment_id=compartment_id,
            compartment_id_in_subtree=True
        )
        compartments = list_compartments_response.data
        
        for compartment in compartments:
            if compartment.lifecycle_state == 'ACTIVE':
                all_compartments.append({
                    'name': compartment.name,
                    'ocid': compartment.id
                })
                
    except oci.exceptions.ServiceError as e:
        print(f"Error listing compartments for {compartment_id}: {e}")
        return []
    
    return all_compartments

def print_compartment_tree(config, root_compartment_id):
    """
    Prints a list of all active compartments in a given compartment subtree, 
    including the root compartment itself, with their OCIDs and names.

    Args:
        config (dict): OCI SDK configuration dictionary.
        root_compartment_id (str): The OCID of the root compartment to start the traversal.
    """
    
    # Fetch the root compartment information
    try:
        identity_client = oci.identity.IdentityClient(config)
        root_compartment = identity_client.get_compartment(compartment_id=root_compartment_id).data
        if root_compartment.lifecycle_state == 'ACTIVE':
            print(f"Name: {root_compartment.name}\nOCID: {root_compartment.id}\n")
    except oci.exceptions.ServiceError as e:
        print(f"Error fetching root compartment {root_compartment_id}: {e}")
        return

    compartments_to_traverse = get_compartment_tree(config, root_compartment_id)
    
    for compartment in compartments_to_traverse:
        print(f"Name: {compartment['name']}\nOCID: {compartment['ocid']}\n")

if __name__ == '__main__':
    # Load the default OCI config
    parser = argparse.ArgumentParser(description='Recursively print OCI compartment tree.')
    parser.add_argument('--profile', type=str, default='DEFAULT', help='The OCI config file profile to use.')
    args = parser.parse_args()

    # Load the OCI config using the specified profile
    try:
        config = oci.config.from_file(os.environ.get('OCI_CONFIG_FILE', '~/.oci/config'), args.profile)
    except oci.exceptions.ConfigFileNotFound:
        print("OCI config file not found. Please ensure it is located at ~/.oci/config or specified by the OCI_CONFIG_FILE environment variable.")
        exit()
    except Exception as e:
        print(f"An error occurred loading the OCI config: {e}")
        exit()

    # Get the tenancy OCID from the config
    tenancy_id = config.get("tenancy")
    if not tenancy_id:
        print("Tenancy OCID not found in the OCI config.")
        exit()

    print_compartment_tree(config, tenancy_id)

