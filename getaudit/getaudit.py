import argparse
import oci
import json
import datetime
from oci.audit.audit_client import AuditClient
from oci.audit.models import ListEventsDetails

def get_audit_events_streamed(
    audit_client: AuditClient,
    compartment_id: str,
    start_time: str,
    end_time: str,
    limit: int,
    output_filename: str,
    event_type: str = None
):
    """
    Fetches OCI Audit events, handling pagination and writing each page 
    incrementally to a JSON file to conserve memory.

    :param audit_client: The initialized AuditClient object.
    :param compartment_id: The OCID of the compartment to query.
    :param start_time: The starting timestamp (RFC 3339 format).
    :param end_time: The ending timestamp (RFC 3339 format).
    :param limit: The maximum number of records per API call (page size).
    :param output_filename: The path to the output JSON file.
    :param event_type: Optional event name to filter by.
    """
    
    print(f"Starting audit export for Compartment: {compartment_id}")
    print(f"Time Range: {start_time} to {end_time}")
    print(f"Page Size (Limit): {limit}")
    
    # Optional filter construction
    query = None
    if event_type:
        # JMESPath query to filter on the eventName field
        query = f'[?"data.eventName" == \'{event_type}\']'
        print(f"Filtering by Event Type: {event_type} (JMESPath: {query})")

    try:
        # 1. Open the file and write the opening JSON array bracket
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write('[\n')
            
            # Pagination variables
            next_page = None
            is_first_record = True
            page_count = 0

            while True:
                page_count += 1
                print(f"Fetching page {page_count}...")
                
                # Make the list_events call
                response = audit_client.list_events(
                    compartment_id=compartment_id,
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit,
                    page=next_page,
                    query=query
                )
                
                # Process events in the current page
                for event in response.data:
                    # Convert the OCI SDK model (AuditEvent) to a dictionary for JSON dumping
                    event_dict = oci.util.to_dict(event)
                    
                    # 2. Add comma separator if it's NOT the first record in the entire file
                    if not is_first_record:
                        f.write(',\n')
                    else:
                        is_first_record = False
                    
                    # 3. Write the JSON object for the event
                    # Use json.dumps to serialize the dictionary, indent for readability
                    json.dump(event_dict, f, indent=4)
                
                # Check for more pages
                next_page = response.opc_next_page
                
                if not next_page:
                    break  # Exit loop if no more pages

            # 4. Write the closing JSON array bracket
            f.write('\n]')
        
        print(f"\n✅ Export complete! Total pages fetched: {page_count}.")
        print(f"Results saved to: {output_filename}")

    except oci.exceptions.ServiceError as e:
        print(f" OCI Service Error: {e.code} - {e.message}")
    except Exception as e:
        print(f" An unexpected error occurred: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="OCI Audit Log Exporter. Fetches events within a time range and writes them to a single JSON file.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Required Arguments
    parser.add_argument(
        '--start-date',
        required=True,
        help='Start date and time (RFC 3339 format, e.g., 2025-11-01T00:00:00Z).'
    )
    parser.add_argument(
        '--end-date',
        required=True,
        help='End date and time (RFC 3339 format, e.g., 2025-11-08T23:59:59Z).'
    )
    
    # Optional Arguments
    parser.add_argument(
        '--compartment-id',
        required=False, # Now optional
        default=None,
        help='The OCID of the compartment to retrieve audit events from. Defaults to the Tenancy OCID from the OCI config profile if not provided.'
    )
    parser.add_argument(
        '--profile',
        type=str,
        default='DEFAULT',
        help='The name of the OCI configuration profile to use (e.g., DEFAULT or a custom profile). Default is DEFAULT.'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Pagination size (number of records per API call). Max allowed is 1000. Default is 50.'
    )
    parser.add_argument(
        '--event-type',
        type=str,
        default=None,
        help='Optional. Filters events by the API operation name (e.g., DeleteInstance, CreateGroup).'
    )
    parser.add_argument(
        '--output-file',
        type=str,
        default='audit_events_export.json',
        help='The name of the output file (default: audit_events_export.json).'
    )

    args = parser.parse_args()

    # Max limit for list_events is 1000
    if args.limit > 1000:
        print("Warning: The 'limit' parameter is capped at 1000 for the OCI Audit Service. Using 1000.")
        args.limit = 1000

    # 1. Configure the OCI SDK using the specified profile
    try:
        config = oci.config.from_file(profile_name=args.profile)
    except oci.exceptions.ConfigFileNotFound:
        print(f" Error: OCI configuration file not found or profile '{args.profile}' does not exist.")
        return
    except Exception as e:
        print(f" Error loading OCI configuration: {e}")
        return

    # 2. Determine the Compartment ID
    final_compartment_id = args.compartment_id
    if final_compartment_id is None:
        # If compartment-id is not provided, use the tenancy OCID from the config
        if 'tenancy' in config:
            final_compartment_id = config['tenancy']
            print(f"Using Tenancy OCID from profile '{args.profile}' as compartment-id: {final_compartment_id}")
        else:
            print("❌ Error: No '--compartment-id' provided and 'tenancy' OCID is missing from the OCI configuration profile.")
            return

    # 3. Initialize the Audit Client
    audit_client = oci.audit.AuditClient(config)

    # 4. Call the streaming function
    get_audit_events_streamed(
        audit_client=audit_client,
        compartment_id=final_compartment_id,
        start_time=args.start_date,
        end_time=args.end_date,
        limit=args.limit,
        output_filename=args.output_file,
        event_type=args.event_type
    )

if __name__ == '__main__':
    # Add a note about dependencies
    print("This script requires the 'oci' Python SDK. Install it using: pip install oci\n")
    main()