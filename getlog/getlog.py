import oci
import threading
import datetime
import logging
import sys
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_audit_logs(config, start_time, end_time, compartment_id, log_group_name, log_name):
    """
    Retrieves audit logs for a specific time range using Oracle Cloud Infrastructure (OCI) SDK.

    Args:
        config (dict): OCI configuration dictionary.
        start_time (datetime.datetime): The start time for the audit log retrieval.
        end_time (datetime.datetime): The end time for the audit log retrieval.
        compartment_id (str): The OCID of the compartment to query.
        log_group_name (str): The name of the log group.
        log_name (str): The name of the log.

    Returns:
        list: A list of audit log entries (dictionaries) or None on error.
    """
    try:
        # Initialize the Audit client
        audit_client = oci.audit.AuditClient(config)

        # Format time as required by the OCI SDK
        start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
        end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S.%f%z')

        logging.info(f"Thread {threading.current_thread().name}: Retrieving logs from {start_time_str} to {end_time_str}")

        # Build the search query.  Important:  The query must specify a time range.
        query = (
            f"AuditEventTime >= '{start_time_str}' AND AuditEventTime <= '{end_time_str}' "
            f"AND compartmentId = '{compartment_id}'" #Added compartment ID to the query
        )
        if log_group_name and log_name:
            query += f" AND logGroupName = '{log_group_name}' AND logName = '{log_name}'"

        # Retrieve audit events
        response = audit_client.search(
            search_details=oci.audit.models.SearchDetails(
                query=query,
                # Add type: "AuditEvent" to the SearchDetails
                type="AuditEvent"
            )
        )

        if response.status != 200:
            logging.error(f"Thread {threading.current_thread().name}: Error retrieving logs: {response.status} - {response.data}")
            return None

        # The response.data is already the Search object, which contains the list of items.
        return response.data.items

    except Exception as e:
        logging.error(f"Thread {threading.current_thread().name}: An error occurred: {e}")
        return None



def process_logs(logs, thread_name):
    """
    Processes the retrieved audit logs.  This function is run by each thread.

    Args:
        logs (list): The list of audit log entries to process.
        thread_name (str): The name of the thread.
    """
    if logs is None:
        logging.warning(f"Thread {thread_name}: No logs to process.")
        return

    try:
        for log_entry in logs:
            # Process each log entry here.  For demonstration, we'll just print a few fields.
            logging.info(f"Thread {thread_name}: Event Time: {log_entry.event_time}, Action: {log_entry.action}, Principal: {log_entry.principalId}")
            #  Example of how to access the full data (useful for debugging)
            #  logging.info(f"Thread {thread_name}: Full Log Entry: {log_entry}")
    except Exception as e:
        logging.error(f"Thread {thread_name}: Error processing log entry: {e}")

def main(num_threads, days_to_fetch, compartment_id, log_group_name=None, log_name=None):
    """
    Retrieves audit logs for a specified number of days using multiple threads.

    Args:
        num_threads (int): The number of threads to use.
        days_to_fetch (int): The number of days to retrieve logs for.
        compartment_id (str): The OCID of the compartment to query.
        log_group_name (str, optional): The name of the log group. Defaults to None.
        log_name (str, optional): The name of the log. Defaults to None.
    """
    try:
        # Load the OCI configuration
        config = oci.config.from_file()
    except oci.exceptions.ConfigFileNotFound as e:
        logging.error(f"OCI configuration file not found: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error loading OCI configuration: {e}")
        sys.exit(1)

    # Get the OCI Compartment ID.
    if not compartment_id:
        logging.error("Compartment ID is required.  Please provide the compartment_id.")
        sys.exit(1)

    # Calculate the time range
    end_time = datetime.datetime.now(datetime.timezone.utc)
    # Calculate the start time
    start_time = end_time - datetime.timedelta(days=days_to_fetch)

    # Calculate the time increment for each thread.  We divide the total time range
    # into num_threads chunks.
    time_increment = datetime.timedelta(seconds=(end_time - start_time).total_seconds() / num_threads)

    threads = []
    for i in range(num_threads):
        # Calculate the start and end time for this thread's chunk
        thread_start_time = start_time + i * time_increment
        thread_end_time = thread_start_time + time_increment

        # Create a new thread
        thread = threading.Thread(
            target=lambda: process_logs(
                get_audit_logs(config, thread_start_time, thread_end_time, compartment_id, log_group_name, log_name),
                threading.current_thread().name
            ),
            name=f"Thread-{i+1}"  # Give the thread a meaningful name
        )
        threads.append(thread)
        thread.start() # start the thread.

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    logging.info("All threads completed.")

if __name__ == "__main__":
    # Get inputs from the user or environment variables
    num_threads = int(input("Enter the number of threads: "))
    days_to_fetch = int(input("Enter the number of days to fetch logs for: "))
    compartment_id = input("Enter the Compartment ID: ")  # Get compartment ID
    log_group_name = input("Enter the Log Group Name (optional, press Enter to skip): ")
    log_name = input("Enter the Log Name (optional, press Enter to skip): ")

    # Call the main function
    main(num_threads, days_to_fetch, compartment_id, log_group_name, log_name)
