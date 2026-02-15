
import oci
import argparse
import json
import re
import pandas as pd
from datetime import datetime, timedelta, timezone
from oci.util import to_dict
from oci.pagination import list_call_get_all_results



"""gcreport.py

Small utility to fetch Cloud Guard problems from OCI and export them to
an Excel workbook. This module queries Cloud Guard for problems in the
tenancy, enriches results with compartment names and a billing tag value
(`ResourceCreator`), and writes a flattened sheet of problems.

Only comments and formatting have been added; the script's runtime
behavior and logic are unchanged.
"""


# Static variables

# Key constants used for dictionary indexing (UPPERCASE key names)
KEY_ID = "id"
KEY_COMPARTMENT_NAME = "CompartmentName"
KEY_RISK_LEVEL = "risk_level"
KEY_RISK_SCORE = "risk_score"
KEY_RESOURCE_NAME = "resource_name"
KEY_RESOURCE_TYPE = "resource_type"
KEY_RESOURCE_CREATOR = "resource_creator"
KEY_LABELS = "labels"
KEY_DETECTOR_RULE_ID = "detector_rule_id"
KEY_RESOURCE_ID = "resource_id"
KEY_TIME_FIRST = "time_first_detected"
KEY_TIME_LAST = "time_last_detected"
KEY_LIFECYCLE_STATE = "lifecycle_state"
KEY_LIFECYCLE_DETAIL = "lifecycle_detail"
KEY_DETECTOR_ID = "detector_id"
KEY_REGION = "region"
KEY_TARGET_ID = "target_id"
KEY_LOCKS = "locks"
KEY_COMPARTMENT_ID = "compartment_id"

# Tags namespace/keys
KEY_BILLING = "billing"
KEY_TAG_RESOURCE_CREATOR = "ResourceCreator"


def createExcel(problems, output_file="output.xlsx"):
    """Write the list of problem dicts to an Excel file.

    The function expects `problems` to be a list of dictionaries where
    keys match the `KEY_*` constants defined in this module. The output is
    a single sheet named "Problems" with columns ordered according to
    `column_sequence`.
    """

    # Prepare flat list for the DataFrame (copy input list)
    problems_tab = [p for p in problems]

    # Ordered list of columns for the spreadsheet
    column_sequence = [
        KEY_ID,
        KEY_COMPARTMENT_NAME,
        KEY_RISK_LEVEL,
        KEY_RISK_SCORE,
        KEY_RESOURCE_NAME,
        KEY_RESOURCE_TYPE,
        KEY_RESOURCE_CREATOR,
        KEY_LABELS,
        KEY_DETECTOR_RULE_ID,
        KEY_RESOURCE_ID,
        KEY_TIME_FIRST,
        KEY_TIME_LAST,
        KEY_LIFECYCLE_STATE,
        KEY_LIFECYCLE_DETAIL,
        KEY_DETECTOR_ID,
        KEY_REGION,
        KEY_TARGET_ID,
        KEY_LOCKS,
        KEY_COMPARTMENT_ID,
    ]

    # Convert to DataFrame and reorder columns (missing columns will appear
    # as NaN in the output; this preserves the original script semantics).
    df1 = pd.DataFrame(problems_tab)
    df1 = df1.reindex(columns=column_sequence)

    # Write the workbook with a single sheet named 'Problems'
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df1.to_excel(writer, sheet_name="Problems", index=False)

    print(f"Excel file created: {output_file}")





# Global cache to prevent redundant API calls for the same resource
resource_cache = {}



def getConfig(config_file=None, profile="Default"):
    """Load OCI configuration from file.

    Args:
        configFile (str): Optional path to config file.
        profile (str): Profile name in the config file.

    Returns:
        dict: Parsed OCI config.
    """

    if config_file is None:
        config = oci.config.from_file(profile_name=profile)
    else:
        config = oci.config.from_file(file_location=config_file, profile_name=profile)
    return config


# Global cache to prevent redundant API calls for the same resource
resource_cache = {}


def getCloudGuardProblems(oci_config, criticality, problem_name=None):
    """
    Fetches Cloud Guard problems and appends the 'Billing.resourcecreator' tag.
    """

    # 
    # Alocate resoruce clients
    #
    cg_client = oci.cloud_guard.CloudGuardClient(oci_config)
    search_client = oci.resource_search.ResourceSearchClient(oci_config)
    identity_client = oci.identity.IdentityClient(oci_config)
    compartment_id = oci_config["tenancy"]
    
    # Calculate 30-day window
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    criticality_list = [c.strip().upper() for c in criticality.split(';')]
    all_filtered_problems = []
    regex = re.compile(problem_name, re.IGNORECASE) if problem_name else None

    for level in criticality_list:
        try:
            # Use pagination helper for efficiency
            response = list_call_get_all_results(
                cg_client.list_problems,
                compartment_id=compartment_id,
                compartment_id_in_subtree=True,
                risk_level=level,
                time_last_detected_greater_than_or_equal_to=thirty_days_ago,
                access_level="ACCESSIBLE"
            )
            
            for item in response.data:
                p_dict = to_dict(item)
                #print(json.dumps(p_dict,indent=2))
                # Apply Regex filter if problem_name is provided
                if regex:
                    target = p_dict.get(KEY_RESOURCE_NAME) or ""
                    if not regex.search(target):
                        continue
                
                # Lookup Creator using the Billing namespace logic

                res_id = p_dict.get(KEY_RESOURCE_ID)
                p_dict[KEY_RESOURCE_CREATOR] = getResourceCreator(
                    search_client=search_client, resource_ocid=res_id
                )
                cmp_id = p_dict.get(KEY_COMPARTMENT_ID, None)
                if cmp_id is not None:
                    compartment = identity_client.get_compartment(cmp_id).data
                    p_dict[KEY_COMPARTMENT_NAME] = compartment.name
                all_filtered_problems.append(p_dict)
                    
        except oci.exceptions.ServiceError as e:
            print(f"Service Error for {level}: {e.message}")

    return all_filtered_problems   


def getResourceCreator(resource_ocid, search_client):
    """
    Looks up a resource by OCID via Resource Search and returns:
      definedTags['billing']['resourcecreator'] if present, else None.
    """

    query = f"query all resources where identifier = '{resource_ocid}'"
    details = oci.resource_search.models.StructuredSearchDetails(query=query)

    resp = search_client.search_resources(details)
    items = resp.data.items or []
    if not items:
        return None

    defined_tags = to_dict(items[0].defined_tags) or {}
    return defined_tags.get(KEY_BILLING, {}).get(KEY_TAG_RESOURCE_CREATOR, None)

#
#
# Main
#


def main():
    """Command-line entry point for listing resources and exporting results."""

    parser = argparse.ArgumentParser(description="resource extractor")
    parser.add_argument("--configfile", type=str, default="~/.oci/config", help="OCI Config file")
    parser.add_argument("--profile", type=str, default="default", help="OCI Profile")
    parser.add_argument("--outfile", type=str, default='problems.xlsx', help="Output file, stdout if not set")
    parser.add_argument("--level", type=str, default='CRITICAL', help = 'comma separated list of criticalty level')
    parser.add_argument("--problem", type=str, default=None, help="problem name, uses rexexp")
    args = parser.parse_args()


    # Allocate the OCI config
    oci_config = getConfig(args.configfile, args.profile)

    if oci_config is None:
        print("Invalid OCI CLI config or OCI CLI config not found")
        print("Usage:")
        print("Options:")
        print(" --configfile      OCI Config file (default: ~/.oci/config)")
        print(" --profile         OCI Profile to use (default: default)")
        print(
            " --outfile         Output file; if not set, output is printed to stdout, save to csv if set"
        )
        print(f" --level      comma separated list of criticalty level")
        print(" --problem  OCID of the root compartment for the search (required)")
        return 1


    # Get all Cloudguard problems 
    problems = getCloudGuardProblems(oci_config, criticality=args.level, problem_name=args.problem)

    #search_client = oci.resource_search.ResourceSearchClient(OCI_Config)
    #print(get_resource_creatorV2(search_client = search_client, ocid=args.problem))
    # Export results to Excel
    createExcel(problems, output_file=args.outfile)

if __name__ == "__main__":
    main()
