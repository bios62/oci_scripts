import oci
import argparse

#
# Global values for recursion
#
maxRecursions = 10
totalProcessed = 0
identity_client = None
listFunction = None
OCI_Config = None
compute_client = None
emptyCompartment = True  # Dont print values for empty compartments
missing_agents = []


def listResources( compartment_id, compartment_name, level):

    global totalProcessed, maxRecursions, listFunction, identity_client, missing_agents

    totalProcessed=totalProcessed+1


    # Assume a valid identity client
    # List child compartments with lifecycle_state == ACTIVE

    # Process current compartment
    compartment = identity_client.get_compartment(compartment_id).data
    if listFunction is not None:
        listFunction(compartment)
    else:
        if compartment_name is None:
            compartment_name = "Root"
        print(f"Parent compartment: {compartment_name} Name: {compartment.name}, OCID: {compartment.id} ")

    compartments = oci.pagination.list_call_get_all_results(
        identity_client.list_compartments,
        compartment_id=compartment_id,
        compartment_id_in_subtree=False,
        access_level="ANY"
    ).data
    if compartments is not None:
        for compartment in compartments:
            if compartment.lifecycle_state == "ACTIVE":
                # print("  " * level + f"Name: {compartment.name}, OCID: {compartment.id}")
                # Recursively visit subcompartment if limit is not hit
                if maxRecursions == 0 or totalProcessed < maxRecursions:
                    listResources(compartment.id, compartment.name,level + 1)
    #


def listCompute(compartment,listAgents=False):

    global compute_client

    data_collection = {}
    resources = []
    if compute_client is None:
        compute_client = oci.core.ComputeClient(OCI_Config)
    # List all instances in the compartment
    #instances = compute_client.list_instances(compartment_id=compartment.id).data
    instances = oci.pagination.list_call_get_all_results(
        compute_client.list_instances,
        compartment_id=compartment.id
    ).data

    if not instances and not emptyCompartment:
        print(f"No compute instances found in compartment {compartment.id}")
        return None

    for instance in instances:
        #print(f"Compartment: {compartment.id} Instance: {instance.display_name} OCID: {instance.id} Lifecycle State: {instance.lifecycle_state}")
        print(f"Compartment: {compartment.name} Instance OCID: {instance.id} Lifecycle State: {instance.lifecycle_state} Instance name: {instance.display_name}")
        if instance.lifecycle_state == 'RUNNING':
            #listAgentStates(instance.id, compartment.id)
            if listAgents:
                list_oci_agent_status(instance.id)


def listComputeWithAgents(compartment):
    listCompute(compartment,True)   


def listAgentStates_NLU( instance_ocid,compartment_id):
    global OCI_Config
    global missing_agents
    # Create clients

    cloud_agent_client = oci.compute_instance_agent.ComputeInstanceAgentClient(OCI_Config)
    vulnerability_client = oci.vulnerability_scanning.VulnerabilityScanningClient(OCI_Config)

    # List all agent plugins (Cloud Agent, OS Management, etc.)
    print(f"Agent Plugin States for instance {instance_ocid}:")
    try:
        response = cloud_agent_client.list_instance_agent_plugins(instance_id=instance_ocid)
        for plugin in response.data:
            print(f"- Plugin Name: {plugin.name}, Status: {plugin.status}")
            if plugin.name == 'Vulnerability Scanning' and plugin.status != 'RUNNING':
                missing_agents.append({compartment_id, instance_ocid})

    except Exception as e:
        print("No agent plugins are confgured", e)



def listPolicies(compartment):
   
    compartment_id = compartment.id

    # Fetch all policies in the compartment
    policies = oci.pagination.list_call_get_all_results(
        identity_client.list_policies,
        compartment_id=compartment_id
    ).data

    if len(policies) > 0:

        for policy in policies:
            print(f"Compartment: {compartment.name} {compartment_id} Policy Name: {policy.name}", end=' ')
            print(f"Description: {policy.description}")
            if len(policy.statements) > 0:
                for stmt in policy.statements:
                    print(f"  - {stmt}")


def listBlockStorageInfo(unatttached=False):
    config = None

def listBlockStorage():
    return listBlockStorageInfo(False)

def listBlockStorageUnattached():
    return listBlockStorageInfo(True)

def listSubscribedRegions(root_compartment_id):
    """
    List all OCI regions the tenancy is subscribed to.

    Args:
        config (dict): OCI config (parsed from config file or provided directly)
        root_compartment_id (str): OCID of tenancy root compartment

    Returns:
        List[str]: List of region names
    """
    identity = oci.identity.IdentityClient(config)
    regions = []
    try:
        response = identity.list_region_subscriptions(root_compartment_id)
        for region_sub in response.data:
            regions.append(region_sub.region_name)
        return regions
    except Exception as e:
        print(f"Error listing regions: {e}")

def getConfig(configFile=None, profile="Default"):
    if configFile is None:
        config = oci.config.from_file(profile_name=profile)
    else:
        config = oci.config.from_file(file_location=configFile, profile_name=profile)
    return config

def list_oci_agent_status(instance_ocid):
    """
    Lists the status of all OCI agents (plugins) on a specified compute instance.

    Args:
        instance_ocid (str): The OCID of the compute instance.

    Returns:
        dict: A dictionary where keys are agent names and values are their statuses,
              or None if the instance is not found or an error occurs.
    """
    try:
  
        # Initialize the ComputeClient to get the instance details (specifically, its compartment_id)
        compute_client = oci.core.ComputeClient(OCI_Config)

        # Get the instance details to retrieve the compartment ID
        try:
            get_instance_response = compute_client.get_instance(instance_id=instance_ocid)
        except:
            print(f"Fetch of instance with ocid: {instance_ocid} failed")
            return 1
        instance_data = get_instance_response.data
        compartment_id = instance_data.compartment_id

        # Initialize the PluginClient to interact with the OCI agents
        plugin_client = oci.compute_instance_agent.PluginClient(OCI_Config)
        
        # Get the list of plugins for the instance
        list_plugins_response = plugin_client.list_instance_agent_plugins(
            instanceagent_id=instance_ocid,
            compartment_id=compartment_id
        )
         
        if list_plugins_response.data is None:
            print("No plugins are confgured")
            return 1
        elif len(list_plugins_response.data) == 0:
            print("No Oracle Cloud Agent plugins found for this instance.")
            return 2
        plugins = list_plugins_response.data
        
        if not plugins:
            print("No Oracle Cloud Agent plugins found for this instance.")
            return 3

        agent_statuses = {}
        print(f"OCI Agent Status for Instance OCID: {instance_ocid}")
        print("-" * 40)
        for plugin in plugins:
            agent_statuses[plugin.name] = plugin.status
            print(f"  - Plugin Name: {plugin.name:<20} | Status: {plugin.status}")

        return agent_statuses

    except oci.exceptions.ServiceError as e:
        print(f"OCI ServiceError: {e.code} - {e.message}")
        # Return None to indicate failure
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # Return None to indicate failure
        return None

def main():

    #
    global listFunction, identity_client, OCI_Config

    resources='Resource  compartments|compute|compute-agents|compute-scan|block|unattached|policy'
    parser = argparse.ArgumentParser(description="´resource extracter")
    parser.add_argument('--configfile', type=str, default='~/.oci/config', help='OCI Config file')
    parser.add_argument('--profile', type=str, default='default', help='OCI Profile')
    parser.add_argument('--outfile', type=str, default=None, help='Output file, stdout if not set')
    parser.add_argument('--resource', type=str, required=True, help=resources)
    parser.add_argument('--compartment-id', default=None, type=str, required=False, help='root compartment of search')
    args = parser.parse_args()
 
    #
    # Select list funtion based on resurce type
    #  
    if args.resource == 'compartments':
        print("Action: compartments")
        listFunction=None   # implies compartments only
    elif args.resource == 'compute':
        print("Action: Compute")
        listFunction=listCompute
    elif args.resource == 'compute-agents':
        print("Action: Compute with agents")
        listFunction=listComputeWithAgents
    elif args.resource == 'policy':
        listFunction= listPolicies
    elif args.resource == 'block':
        listFunction=listBlockStorage
    elif args.resource == 'unattached':
        listFunction=listBlockStorageUnattached
    else:
        print(f"unknow resource request: {args.resource}")
        return 2

    # Allocate the OCI config
    OCI_Config=getConfig(args.configfile, args.profile)


    if OCI_Config is None:
        print('Invalid OCI CLI config or OCI CLI conifg not found')
        print("Usage: ")
        print("Options:")
        print(" --configfile      OCI Config file (default: ~/.oci/config)")
        print(" --profile         OCI Profile to use (default: default)")
        print(" --outfile         Output file; if not set, output is printed to stdout")
        print(f" --resource       {resources}")
        print(" --compartment-id  OCID of the root compartment for the search (required)")
        return 1

    #
    if args.compartment_id is None:
        compartment_id = OCI_Config['tenancy']
    else:
        compartment_id = args.compartment_id
    # 
    # Setup global values for recursion

    # Create identity client
    identity_client = oci.identity.IdentityClient(OCI_Config)

    # Iterate over all compartments
    listResources(compartment_id, None, level=0)

    # incase there are any compute instances without running vulnerability agents, print it
    if args.resource == 'compute-agents':

        if len(missing_agents) > 0:
            print('Compute resourcues without running vulnerability agent')
            print(missing_agents)
        else:
            print('All running instances runs vulnerability agent')
             
if __name__ == '__main__':
    main()
