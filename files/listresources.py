
import oci
import argparse
import json
import pandas as pd


"""listresources.py

Utilities to collect OCI resources across compartments and optionally
export results to an Excel workbook. This module contains helper functions
to list compute instances, policies, and more. The edits in this file
are limited to formatting and documentation — no runtime logic was changed.
"""


# Static variables
KEY_COMPARTMENTS = "compartments"
KEY_COMPUTE = "compute"
KEY_COMPUTE_AGENTS = "compute-agents"
KEY_POLICY = "policy"
KEY_BLOCK = "block"
KEY_UNATTACHED = "unattached"
KEY_COMPARTMENT = "compartment"
KEY_COMPARTMENT_OCID = "OCID"
KEY_LEVEL = "level"
KEY_CREATOR = "creator"
KEY_BILLING = "billing"
KEY_DEFINED_TAGS = "defined_tags"
KEY_RESOURCE_CREATOR = "ResourceCreator"
KEY_COMPARTMENT_NAME = "compartmentname"
KEY_PARENT_COMPARTMENT = "parentcompartment"
KEY_PARENT = "parent"
KEY_BILLING = "billing"
KEY_RESOURCE_CREATOR = "ResourceCreator"
KEY_RESOURCES = "resources"
KEY_DESCRIPTION = "description"
KEY_STATEMENTS = "statements"
KEY_STATEMENT = "statement"
KEY_RESOURCE_OCID = "OCID"
KEY_DISPLAY_NAME = "name"
KEY_LIFECYCLE_STATE = "state"
KEY_AGENTS = "agents"


# List of actions
# compartments|compute|compute-agents|compute-scan|block|unattached|policy
ACTION_LIST = f"{KEY_COMPARTMENTS}|{KEY_COMPUTE}|{KEY_COMPUTE_AGENTS}|{KEY_BLOCK}|{KEY_UNATTACHED}|{KEY_POLICY}"


# Global values for recursion and clients
maxRecursions = 50  # used for testing; set to 0 in production for unlimited
totalProcessed = 0
identity_client = None
listFunction = None
OCI_Config = None
compute_client = None
emptyCompartment = True  # Don't print values for empty compartments
missing_agents = []



def listResources(compartment_id, parent_name, level, collected_resources):
    """Recursively collect resources for a compartment and its children.

    Parameters:
        compartment_id (str): OCID of the compartment to scan.
        parent_name (str): Name of the parent compartment (or None).
        level (int): Current recursion depth.
        collected_resources (list): Accumulator for resources.

    Returns:
        list: The updated `collected_resources` list.
    """

    global totalProcessed, maxRecursions, listFunction, identity_client, missing_agents

    totalProcessed = totalProcessed + 1

    # Get compartment metadata
    compartment = identity_client.get_compartment(compartment_id).data
    print(
        f"Processing compartment: {compartment.name} Parent: {parent_name}, OCID: {compartment.id} level: {level}"
    )

    # Extract resource creator if present in defined tags
    resource_creator = ""
    if KEY_BILLING in compartment.defined_tags:
        resource_creator = compartment.defined_tags[KEY_BILLING][KEY_RESOURCE_CREATOR]
    print(resource_creator)
    # If parent is None we are at root level
    if parent_name is None:
        parent_name = "Root"

    # Fetch list of resources using the configured list function
    if listFunction is not None:
        resource_list = listFunction(compartment)
        if resource_list is not False and len(resource_list) > 0:
            collected_resources.append(
                {
                    KEY_COMPARTMENT_NAME: compartment.name,
                    KEY_COMPARTMENT_OCID: compartment_id,
                    KEY_PARENT_COMPARTMENT: parent_name,
                    KEY_LEVEL: level,
                    KEY_CREATOR: resource_creator,
                    KEY_RESOURCES: resource_list,
                }
            )
    else:  # Only list compartments
        resource_list = []
        collected_resources.append(
            {
                KEY_COMPARTMENT_NAME: compartment.name,
                KEY_COMPARTMENT_OCID: compartment_id,
                KEY_PARENT_COMPARTMENT: parent_name,
                KEY_LEVEL: level,
                KEY_CREATOR: resource_creator,
            }
        )

    # Recurse into child compartments
    next_compartments = oci.pagination.list_call_get_all_results(
        identity_client.list_compartments,
        compartment_id=compartment_id,
        compartment_id_in_subtree=False,
        access_level="ANY",
    ).data

    if next_compartments is not None:
        for next_compartment in next_compartments:
            if next_compartment.lifecycle_state == "ACTIVE":
                if maxRecursions == 0 or totalProcessed < maxRecursions:
                    collected_resources = listResources(
                        next_compartment.id, compartment.name, level + 1, collected_resources
                    )

    return collected_resources

              

def listCompute(compartment, listAgents=False):
    """List compute instances in a compartment and optionally check agent status.

    Args:
        compartment: Compartment object returned by OCI SDK.
        listAgents (bool): If True, check agent status on running instances.

    Returns:
        False, no compute instances exists for compartment
        instacne_list. List of instances in compartment.
    """

    global compute_client, OCI_Config

    if compute_client is None:
        compute_client = oci.core.ComputeClient(OCI_Config)

    # List all instances in the compartment
    instances = oci.pagination.list_call_get_all_results(
        compute_client.list_instances, compartment_id=compartment.id
    ).data

    if (instances is None) or (instances is False) or (len(instances) == 0):
        print(f"No compute instances found in compartment {compartment.id}")
        return False
    instance_list = {} # Init Dict for return
    with open('dump.json','w') as f:
        f.write(json.dumps(oci.util.to_dict(instances),indent=2))
    
    for instance in instances:
        agent_list={}
        print(50*'*')

        print(instance)
        print(50*'*')
        
        if listAgents and instance.lifecycle_state == "RUNNING":
            agent_list,agent_status=list_oci_agent_status(instance.id)
            if agent_status == 0:
                instance_list[instance.id] = {KEY_DISPLAY_NAME:instance.display_name,
                                        KEY_LIFECYCLE_STATE:instance.lifecycle_state,
                                        KEY_AGENTS:agent_list}
            else:
                instance_list[instance.id] =  {KEY_DISPLAY_NAME:instance.display_name,
                        KEY_LIFECYCLE_STATE:instance.lifecycle_state,
                        KEY_AGENTS:None}
        else:
            instance_list[instance.id] =  {KEY_DISPLAY_NAME:instance.display_name,
                        KEY_LIFECYCLE_STATE:instance.lifecycle_state,
                        KEY_AGENTS:None}
        print(
            f"Compartment: {compartment.name} Instance OCID: {instance.id} Lifecycle State: {instance.lifecycle_state} Instance name: {instance.display_name}"
        )

    return instance_list  # Todo: collect and return resources

def listComputeWithAgents(compartment):
    """Wrapper to list compute instances and include agent checks."""

    return(listCompute(compartment, True))


def listAgentStates_NLU(instance_ocid, compartment_id):
    """List agent plugin states for an instance; track missing vulnerability agent."""

    global OCI_Config, missing_agents

    cloud_agent_client = oci.compute_instance_agent.ComputeInstanceAgentClient(OCI_Config)
    vulnerability_client = oci.vulnerability_scanning.VulnerabilityScanningClient(OCI_Config)

    print(f"Agent Plugin States for instance {instance_ocid}:")
    try:
        response = cloud_agent_client.list_instance_agent_plugins(instance_id=instance_ocid)
        for plugin in response.data:
            print(f"- Plugin Name: {plugin.name}, Status: {plugin.status}")
            if plugin.name == "Vulnerability Scanning" and plugin.status != "RUNNING":
                missing_agents.append({compartment_id, instance_ocid})

    except Exception as e:
        print("No agent plugins are confgured", e)


def listPoliciesV1(compartment):
    """Print policies and statements for a compartment (v1 output).

    This function prints policy names and their statements; it does not
    currently return structured data (TODO).
    """

    compartment_id = compartment.id
    results = []
    print(f"processing compartment {compartment_id}")

    # Fetch all policies in the compartment
    policies = oci.pagination.list_call_get_all_results(
        identity_client.list_policies, compartment_id=compartment_id
    ).data

    if len(policies) > 0:
        for policy in policies:
            print(
                f"Compartment: {compartment.name} {compartment_id} Policy Name: {policy.name}",
                end=" ",
            )
            print(f"Description: {policy.description}")
            if len(policy.statements) > 0:
                for stmt in policy.statements:
                    print(f"  - {stmt}")

    return None  # Todo: collect and return resources

def listPolicies(compartment):
    """ Return list of policies in a compartment as a dict mapping name -> details.
        Return False if there are no compute instances in the compartment
    """

    compartment_id = compartment.id
    all_policies = {}

    # Fetch all policies in the compartment
    policies = oci.pagination.list_call_get_all_results(
        identity_client.list_policies, compartment_id=compartment_id
    ).data

    if len(policies) > 0:
        print(f"compartment: {compartment.name} policies {str(len(policies))}")
        for policy in policies:
            print(policy)
            all_policies[policy.name] = {
                KEY_DISPLAY_NAME: policy.name,
                KEY_RESOURCE_OCID: policy.id,
                KEY_DESCRIPTION: policy.description,
                KEY_STATEMENTS: policy.statements,
            }

        return all_policies

    return False

def listBlockStorageInfo(unatttached=False):
    """Placeholder for listing block storage information (TODO).

    Args:
        unatttached (bool): If True, list unattached block volumes.

    Returns:
        None: Function is a placeholder for future implementation.
    """

    config = None
    return None  # Todo: collect and return resources

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
    global OCI_Config
    identity = oci.identity.IdentityClient(OCI_Config)
    regions = []
    try:
        response = identity.list_region_subscriptions(root_compartment_id)
        for region_sub in response.data:
            regions.append(region_sub.region_name)
        return regions
    except Exception as e:
        print(f"Error listing regions: {e}")
    return None # Todo: collect and return resources

def getConfig(configFile=None, profile="Default"):
    """Load OCI configuration from file.

    Args:
        configFile (str): Optional path to config file.
        profile (str): Profile name in the config file.

    Returns:
        dict: Parsed OCI config.
    """

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
            return False,1
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
            return False,2
        elif len(list_plugins_response.data) == 0:
            print("No Oracle Cloud Agent plugins found for this instance.")
            return False,3
        plugins = list_plugins_response.data
        
        if not plugins:
            print("No Oracle Cloud Agent plugins found for this instance.")
            return False,4

        agent_statuses = {}
        print(f"OCI Agent Status for Instance OCID: {instance_ocid}")
        print("-" * 40)
        for plugin in plugins:
            agent_statuses[plugin.name] = plugin.status
            print(f"  - Plugin Name: {plugin.name:<20} | Status: {plugin.status}")

        return agent_statuses,0

    except oci.exceptions.ServiceError as e:
        print(f"OCI ServiceError: {e.code} - {e.message}")
        # Return None to indicate failure
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # Return None to indicate failure
        return None

#
#. Print the structure. For debug
#     
def printResources(resources):
    for i in range (0,len(resources)):
        compartment_data = resources[i]
        print(f'Compartment: {compartment_data[KEY_COMPARTMENT]} Parent: {compartment_data[KEY__COMPARTMENT]}')
        print(json.dumps(resources[i],indent=2))



def create_excel(resource_data, resource_type, output_file="output.xlsx"):
    # 1. Prepare data for compartment data 
    compartment_tab = []
    # 2. Prepare data for "resource" tab"
    resources_tab = []

    #
    # Iterate over all compartments
    #
    for  i in range (0,len(resource_data)):
        item=resource_data[i]
        print(type(item))
        #
        # Compartment tab parent and level
        # 
        compartment_name=item.get(KEY_COMPARTMENT_NAME)
        resource_creator=item.get(KEY_DEFINED_TAGS, {}) \
                       .get(KEY_BILLING, {}) \
                       .get(KEY_RESOURCE_CREATOR, '')
        print(60*'#')
        print(item.get(KEY_DEFINED_TAGS, {}))
        print(60*'#')
        compartment_tab.append(
        {
            KEY_COMPARTMENT:  compartment_name,
            KEY_COMPARTMENT_OCID: item.get(KEY_COMPARTMENT_OCID),
            KEY_PARENT: item.get(KEY_PARENT_COMPARTMENT),
            KEY_LEVEL: item.get(KEY_LEVEL),
            KEY_CREATOR: resource_creator
        })
        #
        # tab Resources: Flattening Resources based on resource type
        #
        resources = item.get("resources", {})
        print(resources)
        for res_id, res_data in resources.items():
            description = res_data.get("description")

            
            print(f"Resource: {res_id} | Description: {description}")
            # todo: create tag
            #
            # Process each resource type
            #
            if resource_type == KEY_POLICY:
                # Iterate over the statements list
                statements = res_data.get(KEY_STATEMENTS, [])
                for statement in statements:
                    resources_tab.append({KEY_COMPARTMENT: compartment_name,
                                          KEY_POLICY:res_id,KEY_STATEMENT:statement})
            elif resource_type == KEY_COMPUTE:
                print(f"Action: Processing {KEY_COMPUTE}")
                print(res_data)
                instances = res_data.get(KEY_INSTANCE, [])
                for instance in instances:
                    resources_tab.append({KEY_COMPARTMENT: compartment_name,
                                          KEY_RESOURCE_OCID:res_id,KEY_DISPLAY_NAME:instance.display_name})
            elif resource_type == KEY_COMPUTE_AGENTS:
                print(f"Action: Processing {KEY_COMPUTE_AGENTS}")

            elif resource_type == KEY_BLOCK:
                print(f"Action: Processing {KEY_BLOCK}")
            elif resource_type == KEY_UNATTACHED:
                print(f"Action: Processing {KEY_UNATTACHED}")
            else:
                print(f"Unknown resource request: {resource_type}")
                return 2
    #
    # Convert to DataFrames
    # foreacy EXCEl creation
    #
    df1 = pd.DataFrame(compartment_tab)
    df2 = pd.DataFrame(resources_tab)

    # Write to Excel with two tabs
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df1.to_excel(writer, sheet_name='General Info', index=False)
        df2.to_excel(writer, sheet_name=resource_type, index=False)
    
    print(f"Excel file created: {output_file}")

#
#
# Main
#


def main():
    """Command-line entry point for listing resources and exporting results."""

    global listFunction, identity_client, OCI_Config

    collected_resources = []
    resources = "Resource  " + ACTION_LIST

    parser = argparse.ArgumentParser(description="resource extractor")
    parser.add_argument("--configfile", type=str, default="~/.oci/config", help="OCI Config file")
    parser.add_argument("--profile", type=str, default="default", help="OCI Profile")
    parser.add_argument("--outfile", type=str, default=None, help="Output file, stdout if not set")
    parser.add_argument("--resource", type=str, required=True, help=resources)
    parser.add_argument(
        "--compartment-id",
        default=None,
        type=str,
        required=False,
        help="root compartment of search",
    )
    args = parser.parse_args()

    # Select list function based on resource type
    resource_type = args.resource
    if args.resource == KEY_COMPARTMENTS:
        print("Action: compartments")
        listFunction = None  # implies compartments only
    elif args.resource == KEY_COMPUTE:
        print("Action: Compute")
        listFunction = listCompute
    elif args.resource == KEY_COMPUTE_AGENTS:
        print("Action: Compute with agents")
        listFunction = listComputeWithAgents
    elif args.resource == KEY_POLICY:
        listFunction = listPolicies
    elif args.resource == KEY_BLOCK:
        listFunction = listBlockStorage
    elif args.resource == KEY_UNATTACHED:
        listFunction = listBlockStorageUnattached
    else:
        print(f"unknow resource request: {args.resource}")
        return 2

    # Allocate the OCI config
    OCI_Config = getConfig(args.configfile, args.profile)

    if OCI_Config is None:
        print("Invalid OCI CLI config or OCI CLI config not found")
        print("Usage:")
        print("Options:")
        print(" --configfile      OCI Config file (default: ~/.oci/config)")
        print(" --profile         OCI Profile to use (default: default)")
        print(
            " --outfile         Output file; if not set, output is printed to stdout, save to csv if set"
        )
        print(f" --resource       {resources}")
        print(" --compartment-id  OCID of the root compartment for the search (required)")
        return 1

    # Determine root compartment for traversal
    if args.compartment_id is None:
        compartment_id = OCI_Config["tenancy"]
    else:
        compartment_id = args.compartment_id

    # Create identity client
    identity_client = oci.identity.IdentityClient(OCI_Config)

    # Iterate over all compartments and collect resources
    collected_resources = listResources(compartment_id, None, level=0, collected_resources=[])

    # Export results to Excel
    create_excel(collected_resources, resource_type)

    # If computing agents were requested, report missing agents
    if args.resource == "compute-agents":
        if len(missing_agents) > 0:
            print("Compute resourcues without running vulnerability agent")
            print(missing_agents)
        else:
            print("All running instances runs vulnerability agent")


if __name__ == "__main__":
    main()
