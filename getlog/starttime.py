import datetime
from datetime import timedelta

import argparse

#
# Constants
#
DATEFORMAT="%Y-%m-%d"

def calculate_start_end_times(date_str, days_offset=0):
    """
    Calculates the start and end times of a day, 5 days prior to the input date.

    Args:
        date_str (str): A date string in YYYY-MM-DD format.

    Returns:
        tuple: A tuple containing the start time and end time as datetime objects.
               Returns None, None if the input date string is invalid.
    """
    try:
        # Convert the date string to a datetime object
        input_date = datetime.datetime.strptime(date_str, DATEFORMAT)  # Corrected format string
    except ValueError:
        print("Error: Invalid date format. Correct Format ": +DATEFORMAT)
        print("Date string attempted to convert: "+date_str)
        return None, None

    # Subtract 5 days
    if days_offset == 0 :
        past_date = input_date
    else:
        past_date = input_date - timedelta(days=days_offset)

    # Calculate the start of the day (00:00:00)
    start_time = past_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Calculate the end of the day (23:59:59)
    end_time = past_date.replace(hour=23, minute=59, second=59, microsecond=0)

    return start_time, end_time


def process_date_range(start_date_str, end_date_str, chunk_size):
    """
    Processes a range of dates in chunks.

    Args:
        start_date_str (str): The start date in YYYY-MM-DD format.
        end_date_str (str): The end date in YYYY-MM-DD format.
        chunk_size (int): The number of days in each chunk.
    """
    try:
        # Convert the date string to a datetime object
        input_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")  # Corrected format string
    except ValueError:
        print("Error: Invalid date format. Please use YYYY-MM-DD.")
        print("Date string attempted to convert: "+date_str)
        return None, None
    current_date = start_time
    while current_date <= end_time_calc:
        chunk_end_date = current_date + timedelta(days=chunk_size - 1) #subtract one day since current date is inclusive
        if chunk_end_date > end_time_calc:
            chunk_end_date = end_time_calc

        print(f"Processing chunk from {current_date.strftime('%Y-%m-%d')} to {chunk_end_date.strftime('%Y-%m-%d')}")
        # Add your processing logic here
        current_date = chunk_end_date + timedelta(days=1)  # Move to the next chunk, added +1 day


def main():
    """
    Main function to parse command line arguments and process the date range.
    """
    parser = argparse.ArgumentParser(description="Process date range in chunks.")
    parser.add_argument("--startdate", help="Start date in YYYY-MM-DD format")
    parser.add_argument("--enddate", help="End date in YYYY-MM-DD format")
    parser.add_argument("--chunksize", type=int, help="Number of days per chunk")

    args = parser.parse_args()

    process_date_range(args.startdate, args.enddate, args.chunksize)


if __name__ == "__main__":
    main()
