#!/bin/bash
# 
#  (c) Inge Os 2025
#  Version: 1.0
#
# Usage: ./startstop.bash config_file instancename start|stop
#
# Start Pythonxa startstopp.py script to change state of compute instance on OCI, with 
# OCI profile configuration and OCID of the instance as input parameter sto the python script
#
# function
# List all configured instaces in config file, caled if illegal compute instanc ename is provided
#
list_instance_names() {
    echo "--- Available Instance Names ---"
    if [ ! -f "$JSON_FILE" ]; then
        echo "Error: JSON file '$JSON_FILE' not found."
        return 1
    fi

    # Use jq to extract all instance_name fields
    # .[] iterates over the array elements, and .instance_name extracts the value.
    jq -r '.[].instance_name' "$JSON_FILE"
    echo "--------------------------------"
    return 0
}

#
# Print the usage 
#
print_usage()
{
   echo "0: Usage: $0 config_file instancename start|stop"
}

# --- Configuration ---
#JSON_FILE="./instances.json"
JSON_FILE=$1

# --- User Input ---
# The script expects the INSTANCE_NAME as the first command-line argument.
INSTANCE_NAME="$2"

# Check if an instance name was provided
if [ -z "$INSTANCE_NAME" ]; then
    echo "Error: Please provide an instance name as an argument."
    print_usage
    exit 1
fi

# Check if the JSON file exists
if [ ! -f "$JSON_FILE" ]; then
    echo "Error: JSON file '$JSON_FILE' not found."
    print_usage
    exit 1
fi

#
#  Check command
#
COMMAND=$3
if [ -z $COMMAND ]; then
   echo "Command needs to be set, start|stop"
   print_usage
   exit 1
fi

set COMMAND = `echo $3 | tr '[A-Z]' '[a-z]'`
if [[ $COMMAND  != "start" && $COMMAND != "stop" ]]; then
  echo " Unknown  command: $COMMAND"
  print_usage
  exit 1
fi
# --- Extract required fields from JSON file using jq ---
# Use jq to filter the array by instance_name and extract the four required fields.
# .[] | select(.instance_name == "$INSTANCE_NAME"): Iterates over objects and filters by name.
# [.compartment_id, .profilename, .instanse_id]: Creates a JSON array of the three required values.
# @tsv: Formats the output as Tab-Separated Values, which is easy to read into shell variables.
# -r: raw output, ensuring no quotes are around the strings.
# The entire command is run in a subshell, and its output is piped into 'read'.
read COMPARTMENT_OCID PROFILE COMPUTE_OCID <<< $(
    jq -r --arg name "$INSTANCE_NAME" '
        .[] | 
        select(.instance_name == $name) | 
        [.compartment_id, .profilename, .instance_id] | @tsv
    ' "$JSON_FILE"
)
echo $COMPUTE_OCID
# Check if the variables were successfully populated
if [ -z "$COMPARTMENT_OCID" ]; then
    echo "Error: Instance '$INSTANCE_NAME' not found in '$JSON_FILE'."
    list_instance_names
    exit 1
fi

# Check if the variable COMPUTE_OCID was successfully populated
if [ -z "$COMPUTE_OCID" ]; then
    echo "Error: compute_ocid was not set for '$INSTANCE_NAME' in '$JSON_FILE'."
    jq -r --arg name "$INSTANCE_NAME" '
        .[] | 
        select(.instance_name == $name) 
    ' "$JSON_FILE"
    exit 1
fi

 # Check if the variables profile was successfully populated
if [ -z "$PROFILE" ]; then
    echo "Error: compute_ocid was not set for '$PROFILE' in '$JSON_FILE'."
        jq -r --arg name "$INSTANCE_NAME" '
        .[] | 
        select(.instance_name == $name) 
    ' "$JSON_FILE"
    exit 1
fi

# Export the variables to make them available in the current shell environment
export COMPARTMENT_OCID
export PROFILE
export COMPUTE_OCID
#
# Provide primary VNIC
#
#VNIC_OCID=`oci compute vnic-attachment list --instance-id $COMPUTE_OCID --profile $PROFILE --compartment-id $COMPARTMENT_OCID | jq '.data[0].id' --raw-output`
# echo $VNIC_OCID
#oci --profile $PROFILE network vnic get --vnic-id $VNIC_OCID --query "data.\"network-security-group-ids\"" --raw-output
#exit
#
#  run start/stop command
#
if [ "$COMMAND" == "start" ]
then
  oci compute instance action --action START --instance-id $COMPUTE_OCID --profile $PROFILE
elif [ "$COMMAND" == "stop" ]
then
  oci compute instance action --action SOFTSTOP --instance-id $COMPUTE_OCID --profile $PROFILE
else
  echo "Paremetrs are START|STOP"
fi

