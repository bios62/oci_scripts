import oci
import sys
import argparse
import traceback

def print_objectstorage_namespace(config: dict) -> None:
    """
    Prints the OCI Object Storage namespace using the provided SDK config.

    :param config: OCI SDK config dictionary (from oci.config.from_file())
    """
    object_storage_client = oci.object_storage.ObjectStorageClient(config)

    namespace = object_storage_client.get_namespace().data
    print(f'Namespace: {namespace}')

def main():

    parser=argparse.ArgumentParser(description="iot instance creator")
    parser.add_argument('--profile', type=str, default=None, help='OCI Profile')
    args = parser.parse_args()
    signer=None
    config=None
    #
    # Allocate variables
    #
    iotDomainId="ocid1.iotdomain.oc1.eu-frankfurt-1.amaaaaaa3gkdkiaao5rz7srmnb7d26eumzvgmyubqgaasvvkitixqwoqx4va"
    authId="ocid1.vaultsecret.oc1.eu-frankfurt-1.amaaaaaa3gkdkiaat47m6qowykzgkwbgeedxeaq4hsumsz5fad254vea3jyq"
    #authId="ocid1.key.oc1.eu-frankfurt-1.bfpykv4eaafak.abtheljtkhlosikacuzyspldwi6zubaamkwgbaunzvxdvw6gf77a53ezwr7a"
    #authId="ocid1.vault.oc1.eu-frankfurt-1.bfpykv4eaafak.abtheljrvdvslvqqtb7ymszi2bls32rjfkuht5gzmwkw4mcx26cn7vjeblkq"


    displayName = "DTfrodeV2"
    externalKey="abcdefg"

    if args.profile is not None:
        config = oci.config.from_file(profile=args.profile)
    else: # Use cloud shell 
        config=oci.config.from_file()
    iotclient = oci.iot.IotClient(config)
    #
    # Verify OCI SDK config
    #
    print_objectstorage_namespace(config)

    # Create the twin 
    #
    # Iterate over the 3 possible OCIDS for secret for test

    iotDetails=oci.iot.models.CreateDigitalTwinInstanceDetails(auth_id=authId,iot_domain_id=iotDomainId,display_name=displayName)

    try:
        print("Creating instance")
        print(iotDetails.auth_id)
        response = iotclient.create_digital_twin_instance(
            create_digital_twin_instance_details=iotDetails
            )
        print(response.status)
        print(response.data)
    except:
        print("Exception:")
        traceback.print_exc()

if __name__ == '__main__':
    main()