import csv
import sys
import os
import json
from ckanext.ontario_theme.harvesters.ontario_geohub import OntarioGeohubHarvester



SAMPLE_JSON_PATH = 'sample_geohub.json'
OUTPUT_CSV_PATH = 'geohub_to_odc_mapping.csv'

def main():

	if not os.path.exists(SAMPLE_JSON_PATH):
		print(f"Sample GeoHub JSON file not found: {SAMPLE_JSON_PATH}")
		sys.exit(1)

	with open(SAMPLE_JSON_PATH, 'r', encoding='utf-8') as f:
		geohub_dict = json.load(f)

	harvester = OntarioGeohubHarvester()
	# harvest_object is not used for mapping, so pass None
	package_dict = harvester._make_package_dict(geohub_dict, None)

	# Flatten the mapping for CSV output
	rows = []
	for k, v in package_dict.items():
		if isinstance(v, dict):
			for subk, subv in v.items():
				rows.append({'ODC Field': f'{k}.{subk}', 'Value': subv})
		elif isinstance(v, list):
			rows.append({'ODC Field': k, 'Value': json.dumps(v)})
		else:
			rows.append({'ODC Field': k, 'Value': v})

	with open(OUTPUT_CSV_PATH, 'w', newline='', encoding='utf-8') as csvfile:
		writer = csv.DictWriter(csvfile, fieldnames=['ODC Field', 'Value'])
		writer.writeheader()
		for row in rows:
			writer.writerow(row)

	print(f"Mapping written to {OUTPUT_CSV_PATH}")

if __name__ == '__main__':
	main()