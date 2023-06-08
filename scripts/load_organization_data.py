#!/usr/bin/env python
# coding: utf-8

#import the necessary modules
import requests
import json
from datetime import datetime
import os
from urllib.request import urlopen
import urllib3
import time
import csv

# Setup basic logging.
import logging
logging.basicConfig(filename='ontario-ca-import.log',
                    level=logging.INFO,
                    filemode='w',
                    format='%(asctime)s - %(levelname)s: %(message)s')
## Settings
testing_mode = False

headers = {'Content-type': 'application/json'}

all_orgs = {}

# Use skip to skip over any unwanted packages
# e.g. 'ontario-public-drug-programs-top-chemicals-and-therapeutic-classes'
skip = [
    'condemnations-for-drug-residues-in-provincially-inspected-plants', 
'agri-food-open-for-e-business',
'ontario-courthouse-heritage-status','latitude-and-longitude-of-ontario-courthouses','budget-talks-data',
'budget-talks-evaluation-survey-data','provincial-powers-requests','provincial-heritage-organizations-operating-grant',
'university-enrolment','ontario-research-fund-research-excellence-program','international-strategic-opportunities-program','post-doctoral-fellowship-program', 'public-schools-offering-french-as-a-second-language-fsl-programs','online-learning-course-enrolment-totals-by-course','fuels-price-survey-information','energy-use-and-greenhouse-gas-emissions-for-the-broader-public-sector','organization/environment-conservation-and-parks','beer-manufacturers-microbrewers-and-brands','raw-leaf-tobacco-registrant-list','risk-intake-scoring-database','greenhouse-compliance-and-inspection-database','cooperation-and-exchange-agreement-between-qubec-and-ontario-on-francophonie', 'projects-funded-under-the-ontario-400th-celebrations-program','bilingual-positions-within-the-ontario-public-service-ops','ontario-covid-19-testing-percent-positive-by-age-group','status-of-covid-19-cases-in-ontario','ontario-first-nations-treaty-areas','ministry-of-infrastructure-website-performance-data','small-rural-and-northern-municipal-infrastructure-fund-capacity','consular-offices-in-ontario','contributions-under-the-international-disaster-relief-program','newcomer-settlement-program','recognized-employers-under-the-supporting-ontario-s-safe-employers-program','training-providers-for-working-at-heights','long-term-care-home-ltch-locations','physiotherapy-activity-report-in-long-term-care','assessment-files','ontario-drill-hole-database','greenbelt-river-valley-connections','greenbelt-specialty-crop-areas','moose-tag-allocation-process-results','wolf-and-coyote-hunting-activity-and-harvests','elk-harvests','sudbury-area-team-stakeholder-database','ministry-audit-results-for-common-service-standards','regional-economic-development-branch-cost-assignment-information-for-northern-ontario-heritage-fund','top-northern-ontario-employers','registered-marriage-officiants','covid-19-self-assessment-tool','serviceontario-wait-times-and-call-volumes-contact-centres','seniors-active-living-centre-locations','age-friendly-community-planning-grant-program-approved-projects','status-of-covid-19-cases-in-ontario-s-correctional-institutions','security-guard-and-private-investigative-services-industry-data','police-resources','short-term-rental-statistics','hotel-statistics', 'electric-vehicles-in-ontario-by-forward-sortation-area','ontario-s-highway-programs','ontario-s-highway-programs','2006-commercial-vehicle-survey-origin-and-destination','list-of-provincial-agencies','public-appointment-vacancies','ontario-social-assistance-case-characteristics-by-census-metropolitan-area',
       'social-assistance-caseloads'
    
        
       ]
# Set up api token, from http://localhost/user/edit/admin
api_token = ""

# Define the URLs for Ontario.ca and localhost
site_url = 'https://data.ontario.ca'
dataset_url = site_url + "/dataset/"

# Define the endpoints for packages and resource operations
package_search_endpoint = '{}/api/3/action/package_search'.format(site_url)
print(package_search_endpoint)
# localhost endpoints
localhost_url = "http://localhost"
package_create_endpoint = '{}/api/action/package_create'.format(localhost_url)
resource_create_endpoint = '{}/api/action/resource_create'.format(localhost_url)
resource_patch_endpoint = '{}/api/action/resource_patch'.format(localhost_url)
resource_query_endpoint = '{}/api/3/action/datastore_search'.format(localhost_url)

# Localhost Header with API Tokens
localhost_headers = {
  'Authorization': api_token
}


# Define localhost endpoints for package search and show
local_package_search_endpoint = '{}/api/action/package_search'.format(localhost_url)
local_datastore_search_sql_endpoint = '{}/api/action/datastore_search_sql'.format(localhost_url)
local_package_show_endpoint = '{}/api/action/package_show'.format(localhost_url)

# List of packages and restore attributes
package_attributes = [
  "title_translated",
  "name",
  "notes_translated",
  "colby_notes",
  "asset_type",
  "keywords",
  "geographic_coverage",
  "geographic_granularity",
  "url",
  "owner_org",
  "maintainer_translated",
  "maintainer_email",
  "author",
  "author_email",
  "maintainer_branch",
  "current_as_of",
  "update_frequency",
  "access_instructions",
  "license_id",
  "licence_range_start",
  "licence_range_end",
  "access_level",
  "opened_date",
  "exemption",
  "exemption_rationale",
  "cluster_application_id",
  "go_program_id"
]
resource_attributes = [
  "name_translated",
  "description_translated",
  "type",
  "language",
  "contains_geographic_markers",
  "publically_available_date",
  "data_range_start",
  "data_range_end",
  "data_last_updated",
  "data_birth_date"
]


# Functions for various operations including getting package count, packages by format, organization ID, etc.
# Detailed comments are added above each function definition in the code.

# Get the count of files at a specific path
def get_file_count(file_path):
    with open(file_path) as csvfile:
        rowreader = csv.reader(csvfile)
    
        return sum(1 for row in rowreader)-1
    
# Get a specified number of packages from the server
def get_some_packages():
    packages = []
    start = 0
    count = 1
    if not get_how_many:
        rows = 1000
    elif get_how_many < 1000:
        rows = get_how_many
    else:
        rows = 1000
    while start < count:
        get_req = requests.get(package_search_endpoint + '?rows='+str(rows)+'&start={}'.format(start),
                          headers=headers)
        print('get_req:')
        print(package_search_endpoint + '?rows='+str(rows)+'&start={}'.format(start))
        if count == 1:
            if not get_how_many:
                count = get_req.json()["result"]["count"] 
            else:
                count = get_how_many
        packages = packages + get_req.json()["result"]["results"]
        start = start + 1000
    
    return packages

# Get packages that have at least one resource in a specific format
def get_some_packages_by_format(file_format):
    '''Return packages with at least one resource in the format specified by file_format arg.
    
    '''
    packages = []
    return_packages = []
    start = 0
    count = 1
    if not get_how_many:
        rows = 1000
    elif get_how_many < 1000:
        rows = get_how_many
    else:
        rows = 1000
    while start < count:
        print('start: ', str(start))
        get_req = requests.get(package_search_endpoint + '?rows='+str(rows)+'&start={}'.format(start),
                          headers=headers)
        print('get_req:')
        print(package_search_endpoint + '?rows='+str(rows)+'&start={}'.format(start))
        
        if count == 1:
            if not get_how_many:
                count = get_req.json()["result"]["count"] 
            else:
                count = get_how_many

        packages = packages + get_req.json()["result"]["results"]
        start = start + 1000
        
        format_flag=0
        for idx in range(len(packages)):            
            
            for res_idx in range(len(packages[idx]['resources'])):
                res_format = packages[idx]['resources'][res_idx]['format']
                if res_format == file_format:
                    format_flag = 1
                
            if format_flag==1:
                print('return packages: ', packages[idx]['name'])
                return_packages.append(packages[idx])
            
            # reset
            format_flag=0
    
    return return_packages


# Get the organization ID from the server for a given organization name
def get_org_id(org_name):
    if org_name in all_orgs:
        return all_orgs[org_name]

    org_id = None
    req_org = requests.get('{}/api/3/action/organization_show?id={}'.format(localhost_url, org_name),
                           headers=headers, verify=False)
    if req_org.json()["success"]:
        org_id = req_org.json()["result"]["id"]

    else:
        # Create missing organization to get ID.
        req_org_from_production = requests.post('{}/api/3/action/organization_show?id={}'.format(site_url, org_name),
                               headers=headers, verify=False)
        org_json = req_org_from_production.json()["result"]
        del org_json['id']


        req_org = requests.post('{}/api/3/action/organization_create'.format(localhost_url),
                               json=org_json,
                               headers=localhost_headers)
        org_id = req_org.json()["result"]["id"]
    
    all_orgs[org_name] = org_id
    
    return org_id


# Remove the attributes that we do not want to pass into the request
def dictFilter(the_attributes, the_dict):
    new_dict = {}
    for (key, value) in the_dict.items():
        if key in the_attributes:
            new_dict[key] = value
  
    return new_dict
# For multipart requests, the body is treated as a form and cannot handle nested JSON
# Nested objects must be converted to strings

# Format a dictionary for POST request
def formatForPosting(dictForPosting):
    for key, value in dictForPosting.items():
        if isinstance(value,dict):
            dictForPosting[key] = json.dumps(value)

    return dictForPosting

## Specify number of packages to get
get_how_many = 300
# packages = get_some_packages()


# Get packages that contain CSV resources
file_format='CSV'
packages = get_some_packages_by_format(file_format)

# Dump out extracted packages into a json file
# Save the retrieved packages into a JSON file
stamp = datetime.now().strftime("%Y-%m-%d - %H-%M")
with open('somepackages_csv-'+stamp+'.json', 'w') as outfile:
    json.dump(packages, outfile)
# Number of packages to load
len(packages) + 1
## Make sure XLoader is running
# If XLoader is running, then any resources POSTED to the local FileStore will be automatically queued for the DataStore, and XLoader will try to push them dynamically.  

#```
#$ . /usr/lib/ckan/default/bin/activate
#(default) VirtualBox:~$ ckan -c /etc/ckan/default/ckan.ini jobs worker
#ckan -c /etc/ckan/default/ckan.ini xloader status

#```
## Create package in localhost and add resources
#Get packages and their resources from the live catalogue, then POST them to the local catalogue.  
failed_edc_packages=[]
failed_resource_writes=[]

# Open the file containing the saved packages in JSON format
with open('somepackages_csv-'+stamp+'.json') as file:
    packages = json.load(file)
    #iterate over each paackage in packages
    for package in packages:
        #skip the package if its in the skip list
        if package['name'] in skip:
            continue
          
        print('')
        print('Starting package: ', package['name'])

        org_id = get_org_id(package['organization']['name'])

        package['owner_org'] = org_id
        resources = []
        resources = package['resources']

        to_delete = [
          'id',
          'resources',
          'license_title',
          'num_tags',
          'metadata_created',
          'metadata_modified',
          'relationships_as_subject',
          'num_resources',
          'tags',
          'groups',
          'creator_user_id',
          ]
        for field in to_delete:
            del package[field]

        # Create package in local host
        req = requests.post(package_create_endpoint,
                        json=package,
                        headers=localhost_headers, verify=False)
        logging.info("%s", package['name'])
        logging.info("%s %s", req.status_code, req.reason)

        print(req, req.reason)
            
            
        # Log a message if the package creation is successful
        if not req.status_code == 200:
            # Package failed to be created; store EDC package id:
            failed_edc_packages.append([package['title'],
                                        req.status_code,
                                        req.reason
                                       ])
            print(package['name'] + " package not patched.")
        else:
            # Log an error message if the package creation fails
            print(package['name'] + " package updated.")
            package_id = req.json()['result']['id']

            print('len(resources): ', str(len(resources)))

            # Loop through each resource
            for r in resources:
                print(r['name'])
                original_resource_id = r['id']
                del r['id']
                del r['package_id']

                r['package_id'] = package_id
                resource_file_name = os.path.basename(r['url'])
                write_path = "uploads/"+ package['name'] + "/" + original_resource_id
                if os.path.isdir("uploads") is False:
                    os.mkdir("uploads")
                if os.path.isdir("uploads/"+ package['name']) is False:
                    os.mkdir("uploads/"+ package['name'])
                if os.path.isdir(write_path) is False:
                    os.mkdir(write_path)

                try:

                    
                    with open(write_path+"/"+resource_file_name,'wb') as f:
                        f.write(urlopen(r['url']).read())
                        f.close()
                        del r['url']
                except:
                    print('****** Error writing to ', resource_file_name)
                    failed_resource_writes.append([package['name'],resource_file_name])
                    print('write_path: ', write_path)
                    print('r[url]: ', r['url'])
                    print('')

                payload = dictFilter(resource_attributes, r)
                payload = formatForPosting(payload)
                payload["package_id"] = package_id

                # Push resources to FileStore
                with open(write_path+"/"+resource_file_name,'rb') as output:
                    resp = requests.post(resource_create_endpoint+"?package_id="+payload['package_id'],
                                       data=payload,
                                       headers=localhost_headers,
                                       files=[('upload', output)]
                                  )
                    print('resp: ', resp, resp.reason)
                    logging.info("%s", resource_file_name)
                    logging.info("%s %s", resp.status_code, resp.reason)
                    print('')
