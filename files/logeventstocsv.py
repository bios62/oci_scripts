import pandas as pd
import json
import sys

if len(sys.argv) != 3:
    print("Usage: python extract_audit.py <inputfile.json> <outputfile.csv>")
    sys.exit(1)

inputfile = sys.argv[1]
outputfile = sys.argv[2]

with open(inputfile, 'r') as f:
    data = json.load(f)

# Adjust this if your JSON structure is different
events = data['data'] if 'data' in data else data

df = pd.json_normalize(events)
df.to_csv(outputfile, index=False)

print(f"Extracted data from {inputfile} and saved as {outputfile}.")

