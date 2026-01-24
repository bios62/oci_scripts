import oci
import argparse


def recurseCompartments(config, compartmentId, level=0, resourceFunction=None):
    """
    Recursively iterates through compartments and applies a function to resources.
    """
    identityClient = oci.identity.IdentityClient(config)

    compartment = identityClient.get_compartment(compartmentId)

    print(compartment)
    print(f"Name: {compartment.name}, OCID: {compartment.id}")
    compartments = oci.pagination.list_call_get_all_results(
        identityClient.list_compartments,
        compartment_id=compartmentId,
        compartment_id_in_subtree=False,
        access_level="ANY",
    ).data

    for childCompartment in compartments:
        if childCompartment.lifecycle_state == "ACTIVE":
            resourceFunction(config, childCompartment)
            recurseCompartments(identityClient, childCompartment, level + 1)


def listCompute(config, compartment):
    """
    Lists compute instances in a given compartment.
    """
    computeClient = oci.core.ComputeClient(config)

    instances = oci.pagination.list_call_get_all_results(
        computeClient.list_instances,
        compartment_id=compartment.id,
    ).data

    if not instances:
        print(f"No compute instances found in compartment {compartment.id}")
        return

    print(f"Compute instances in compartment {compartment.id}:\n")
    for instance in instances:
        print(f"Name: {instance.display_name}")
        print(f"OCID: {instance.id}")
        print(f"Lifecycle State: {instance.lifecycle_state}")
        print("-" * 40)


def listPolicies(config, compartment):
    """
    Lists policies in a given compartment.
    """
    identityClient = oci.identity.IdentityClient(config)

    policies = oci.pagination.list_call_get_all_results(
        identityClient.list_policies,
        compartment_id=compartment.id,
    ).data

    if not policies:
        print(f"No policies found in compartment {compartment.id}")
        return

    print(f"Policies in compartment: {compartment.id}\n")
    for policy in policies:
        print(f"Policy Name: {policy.name}")
        print(f"Description: {policy.description}")
        print("Statements:")
        for statement in policy.statements:
            print(f"  - {statement}")
        print("-" * 40)


def listBlockStorageInfo(config, compartment, unattached=False):
    """
    Lists block storage volumes in a given compartment.
    """
    print(config)
    print(compartment)
    print(unattached)


def listBlockStorage(config, compartment):
    """
    Wrapper to list all block storage.
    """
    return listBlockStorageInfo(config, compartment, False)


def listBlockStorageUnattached(config, compartment):
    """
    Wrapper to list unattached block storage.
    """
    return listBlockStorageInfo(config, compartment, True)


def listSubscribedRegions(config, rootCompartmentId):
    """
    List all OCI regions the tenancy is subscribed to.

    Args:
        config (dict): OCI config (parsed from config file or provided directly)
        rootCompartmentId (str): OCID of tenancy root compartment

    Returns:
        List[str]: List of region names
    """
    identityClient = oci.identity.IdentityClient(config)
    regions = []
    try:
        response = identityClient.list_region_subscriptions(rootCompartmentId)
        for regionSub in response.data:
            regions.append(regionSub.region_name)
        return regions
    except Exception as e:
        print(f"Error listing regions: {e}")
        return []


def getConfig(configFile=None, profile="DEFAULT"):
    """
    Retrieves OCI configuration.
    """
    if configFile is None:
        config = oci.config.from_file(profile_name=profile)
    else:
        config = oci.config.from_file(file_location=configFile, profile_name=profile)
    return config


def main():
    """
    Main function to parse arguments and call the appropriate function.
    """
    parser = argparse.ArgumentParser(description="resource extracter")
    parser.add_argument('--config-file', type=str, default=None,
                        help='OCI Config file')
    parser.add_argument('--profile', type=str, default="DEFAULT",
                        help='OCI Profile')
    parser.add_argument('--output-file', type=str, default=None,
                        help='Output file, stdout if not set')
    parser.add_argument('--resource', type=str, required=True,
                        help='Resource compute|block|unattached|policy')
    parser.add_argument('--compartment-id', type=str, required=True,
                        help='root compartment of search')
    args = parser.parse_args()

    listFunction = None
    if args.resource == 'compute':
        listFunction = listCompute
    elif args.resource == 'policy':
        listFunction = listPolicies
    elif args.resource == 'block':
        listFunction = listBlockStorage
    elif args.resource == 'unattached':
        listFunction = listBlockStorageUnattached
    else:
        print(f"unknown resource request: {args.resource}")
        return 2

    config = getConfig(args.config_file, args.profile)
    print(config)

    if config is None:
        print('Invalid OCI CLI config or OCI CLI config not found')
        return 1

    recurseCompartments(config, args.compartment_id, resourceFunction=listFunction)


if __name__ == '__main__':
    main()