#!/bin/bash

# --- Configuration ---
COMPARTMENT_OCID="ocid1.tenancy.oc1..aaaaaaaaflf2uasr2shm5ag2yulp4gjy3aoqvwvvbcmvuk52fndnkps3byra"
DAYS_AGO=2
OUTPUT_FILE="iam_user_audit_events_last_${DAYS_AGO}_days.json"

# --- Calculate Time Range ---
# Calculate the start time for the audit trail (30 days ago) in RFC3339 format (required by OCI)
START_TIME=$(date -u -d "$DAYS_AGO days ago" "+%Y-%m-%dT%H:%M:%SZ")
END_TIME=$(date -u "+%Y-%m-%dT%H:%M:%SZ")
PROFILE="nose-default"
TEMPFILE=$HOME/temp/audit.json
FILTER="identity"
#values for filter:  identity
#
# Additional parameters
#
# ADDITIONALCMDLINE="--debug --raw-output"
# ADDITIONALCMDLINE="--debug"
# ADDITIONALCMDLINE="--raw-output"
#
ADDITIONALCMDLINE=""
if [[ -n $FILTER ]] ; then
  ADDITIONALCMDLINE=${ADDITIONALCMDLINE} " "--query "data[?contains(eventName, '"${FILTER}"')]"
  echo ${ADDITIONALCMDLINE}
fi
CMDLINE=" --profile ${PROFILE} \
    --compartment-id ${COMPARTMENT_OCID} \
    --start-time ${START_TIME} \
    --end-time ${END_TIME} \
    --all " \
    ${ADDITIONALCMDLINE}

echo "Fetching Audit Records from: $START_TIME to $END_TIME"
echo "Target Compartment OCID: $COMPARTMENT_OCID"
echo $CMDLINE
# --- OCI CLI Command and jq Filtering ---
time oci audit event list ${CMDLINE} >$TEMPFILE
cat $TEMPFILE | jq '[
    .[]
    | select(
        # Filter by the User CRUD Success Event IDs
        .data.additionalDetails.eventId == "admin.user.create.success" or
        .data.additionalDetails.eventId == "admin.user.delete.success"
    )
    # Select only the relevant fields for a cleaner output
    | {
        "eventTime": .eventTime,
        "eventId": .data.additionalDetails.eventId,
        "action": .eventType,
        "actor": .data.identity.principalName,
        "targetUser": .data.additionalDetails.targetName,
        "targetUserOCID": .data.additionalDetails.targetId,
        "domainName": .data.additionalDetails.domainName
    }
]' > $OUTPUT_FILE

