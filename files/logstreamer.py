import argparse
import datetime
import json
import sys
import pickle
import time
import re
from typing import List, Tuple, Generator, Dict, Any, Optional

# Attempt to import OCI SDK modules
try:
    import oci
    from oci.audit.audit_client import AuditClient
    from oci.config import from_file
    from oci.pagination import list_call_get_all_results
    from oci.exceptions import ServiceError
    from oci.util import to_dict
except ImportError:
    print("Error: OCI SDK is not installed. Please install it using 'pip install oci'")
    sys.exit(1)


# Global string keys used when indexing dictionaries returned by the OCI SDK
TENANCY = "tenancy"
KEY_DATA = "data"
KEY_EVENT_TYPE = "event_type"
KEY_EVENT_NAME = "event_name"


# --- Custom JSON Encoder for OCI SDK Objects and datetime ---

class OciCustomEncoder(json.JSONEncoder):
    """
    A custom JSON Encoder that handles OCI SDK objects (by converting them to dicts) 
    and datetime objects (by formatting them to ISO 8601 strings).
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            # Format datetime objects as RFC3339 (ISO 8601) strings, 
            # which is the standard used by OCI.
            return obj.isoformat() + 'Z'
        
        # OCI SDK objects often have a to_dict() method for serialization.
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        
        return super().default(obj)


# --- Core Logic Class ---

class OciAuditStreamer:
    """Handles OCI configuration, date chunking, and streaming of audit events."""
    
    # OCI Audit API has a practical time range limit of 14 days per request.
    MAX_CHUNK_DAYS = 7
    
    def __init__(self,  profile_name: str, 
                 start_date: str, end_date: str, oci_config_path: Optional[str] = None):
        """
        Initializes the streamer with configuration and date parameters.
        
        :param profile_name: The profile name from the OCI config file.
        :param start_date: The start date in DD.MM.YY format.
        :param end_date: The end date in DD.MM.YY format.
        :param oci_config_path: Optional path to the OCI config file.
        """

        self.profile_name = profile_name
        self.oci_config_path = oci_config_path
        self.oci_config = None
        
        # Convert date strings to datetime objects
        self.start_dt = self._parse_date(start_date)
        self.end_dt = self._parse_date(end_date) + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)

        # Initialize OCI Client
        self.audit_client = self._initialize_client()
        self.compartment_ocid = self.oci_config[TENANCY]

    def _parse_date(self, date_str: str) -> datetime.datetime:
        """Parses DD.MM.YY string into a datetime object (midnight UTC)."""
        try:
            # Set time to midnight UTC for the start of the day
            return datetime.datetime.strptime(date_str, '%d.%m.%y').replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=datetime.timezone.utc
            )
        except ValueError:
            print(f"Error: Date '{date_str}' is not in the required DD.MM.YY format.")
            sys.exit(1)

    def _initialize_client(self) -> AuditClient:
        """Loads OCI configuration and initializes the AuditClient."""
        try:
            # Load OCI configuration from the specified path or default location
            if self.oci_config_path:
                self.oci_config = from_file(file_location=self.oci_config_path, profile_name=self.profile_name)
            else:
                self.oci_config = from_file(profile_name=self.profile_name)
            
            return AuditClient(self.oci_config)
        except Exception as e:
            print(f"Error initializing OCI client with profile '{self.profile_name}': {e}")
            sys.exit(1)

    def _get_date_chunks(self) -> List[Tuple[datetime.datetime, datetime.datetime]]:
        """
        Splits the total date range into chunks of MAX_CHUNK_DAYS (14 days) or less.
        """
        chunks = []
        current_start = self.start_dt
        max_duration = datetime.timedelta(days=self.MAX_CHUNK_DAYS)

        while current_start <= self.end_dt:
            # Calculate chunk end time (14 days from current_start, minus 1 second to stay within the range)
            chunk_end = min(current_start + max_duration, self.end_dt)

            if chunk_end < current_start:
                # Should not happen if logic is correct, but safe guard.
                break

            chunks.append((current_start, chunk_end))
            
            # Set the next start time to one second after the current chunk_end
            current_start = chunk_end + datetime.timedelta(seconds=1)
        
        return chunks

    def fetch_events_generator(self) -> Generator[Dict[str, Any], None, None]:
        """
        Iterates through date chunks and yields audit events one by one using a generator.
        """
        date_chunks = self._get_date_chunks()
        total_chunks = len(date_chunks)
        event_count = 0

        print(f"Total time range: {self.start_dt.date()} to {self.end_dt.date()}")
        print(f"Fetching in {total_chunks} chunks of max {self.MAX_CHUNK_DAYS} days...")

        for i, (chunk_start, chunk_end) in enumerate(date_chunks):
            print(f"\n--- Processing Chunk {i+1}/{total_chunks}: {chunk_start.date()} to {chunk_end.date()} ---")
            
            try:
                # OCI SDK utility function for automatic pagination handling
                list_events_response = list_call_get_all_results(
                    self.audit_client.list_events,
                    compartment_id=self.compartment_ocid,
                    start_time=chunk_start,
                    end_time=chunk_end
                )

                for event in list_events_response.data:
                #for event in jpayload:
                    yield event
                    event_count += 1
                
                print(f"Chunk {i+1} completed. Events retrieved in this chunk: {len(list_events_response.data)}")

            except ServiceError as e:
                print(f"OCI Service Error in Chunk {i+1} ({chunk_start.date()} to {chunk_end.date()}): {e}")
                # Continue to the next chunk if one fails, or raise the error if fatal
                continue
            except Exception as e:
                print(f"An unexpected error occurred in Chunk {i+1}: {e}")
                continue

        print(f"\nAudit log fetch complete. Total events yielded: {event_count}")

# --- Utility Function for Streaming to File ---

def stream_to_json_file(data_generator: Generator, output_file_path: str, eventfilter :str):
    """
    Writes the data stream (generator) to a file as a single, valid JSON array.
    """
    print(f"Writing results to file: {output_file_path}...")
    
    if eventfilter is not None:
        filters=eventfilter.split(';')
    try:
        all_events={}
        with open(output_file_path, 'w', encoding='utf-8') as f:
            # 1. Write the opening bracket for the JSON array
            f.write('[\n')
   
            is_first = True
            for item in data_generator:
                # 2. Add comma separator before all items except the first
                if not is_first:
                    f.write(',\n')
                
                # 3. Serialize the item (handles OCI objects and datetimes via custom encoder)
                jitem=to_dict(item)
                #
                # only serialize events of interest using regexp
                #
                if eventfilter is None:
                    f.write(json.dumps(jitem, indent=2))
                    is_first = False
                else:
                    for single_filter in filters:
                        in_filter=re.search(single_filter, jitem[KEY_DATA][KEY_EVENT_TYPE])
                        if in_filter:
                            f.write(json.dumps(jitem, indent=2))
                            is_first = False
                            break
                #
                # Collect all event types (One time job
                #
                event_value=jitem[KEY_DATA][KEY_EVENT_NAME]
                if event_value in all_events:
                    all_events[event_value]+=1
                else:
                    all_events[event_value]=0
            # If data was written, ensure the last object is followed by a newline before closing.
            if not is_first:
                 f.write('\n')
            
            # 4. Write the closing bracket
            f.write(']\n')

        print(f"Successfully streamed audit logs to {output_file_path}")
        ff=open('allevents.json','w')
        ff.write(json.dumps(all_events))
        ff.close()
    except IOError as e:
        print(f"Error writing to file {output_file_path}: {e}")
    except Exception as e:
        print(f"An error occurred during JSON streaming: {e}")


# --- Argument Parsing and Execution ---

def main():
    parser = argparse.ArgumentParser(
        description="Fetch OCI Audit Events for a specified time range, splitting the request into 14-day chunks, and streaming the output to a valid JSON file."
    )
    
    # Required arguments
    parser.add_argument('--startdate', required=True, help="Start date in DD.MM.YY format (e.g., 01.12.2025).")
    parser.add_argument('--enddate', required=True, help="End date in DD.MM.YY format (e.g., 01.12.2025). The query fetches up to the end of this day.")
    parser.add_argument('--profilename', required=True, help="The profile name in your OCI configuration file (e.g., DEFAULT).")
    parser.add_argument('--outputfile', required=True, help="The path and filename for the output JSON file (e.g., audit_logs.json).")
    # Using 'eventfilter' for the required Compartment OCID, as explained in the prompt analysis.
    parser.add_argument('--eventfilter', required=False, 
                        help="OCI Compartment OCID (e.g., ocid1.compartment.oc1..aaaaaa...) to fetch audit logs from. This argument is used as the compartment_id.")

    # Optional argument
    parser.add_argument('--ociconfig', default=None, help="Optional path to the OCI configuration file (defaults to ~/.oci/config).")

    args = parser.parse_args()

    # 1. Initialize the Streamer
    try:
        streamer = OciAuditStreamer(
            profile_name=args.profilename,
            start_date=args.startdate,
            end_date=args.enddate,
            oci_config_path=args.ociconfig
        )
    except SystemExit:
        # Exit silently if OCI initialization failed (error message already printed)
        return

    # 2. Get the Generator (event stream)
    event_generator = streamer.fetch_events_generator()

    # 3. Stream results to the JSON file
    stream_to_json_file(event_generator, args.outputfile,args.eventfilter)


if __name__ == '__main__':
    main()