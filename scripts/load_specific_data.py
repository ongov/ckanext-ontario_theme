#!/usr/bin/env python
# coding: utf-8

# import the necessary modules
import logging
import requests
import json
from datetime import datetime
import os
from urllib.request import urlopen
import time
import csv


# Start of config section. Populate these values

# where do you want to load these packages?
localhost_url = "http://localhost"
localhost_headers = {
  'Authorization': ''
}

white_list = ["electric-vehicles-in-ontario-by-forward-sortation-area"]

# End of configuration section.


# Setup basic logging.
logging.basicConfig(
    filename="ontario-ca-import.log",
    level=logging.INFO,
    filemode="w",
    format="%(asctime)s - %(levelname)s: %(message)s",
)

testing_mode = False
site_url = "https://data.ontario.ca"
dataset_url = site_url + "/dataset/"
package_search_endpoint = "{}/api/3/action/package_search".format(site_url)
headers = {"Content-type": "application/json"}

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
    "data_birth_date",
]


def get_file_count(file_path):
    with open(file_path) as csvfile:
        rowreader = csv.reader(csvfile)
        return sum(1 for row in rowreader) - 1


def get_some_packages():
    packages = []
    start = 0
    count = 1
    while start < count:
        get_req = requests.get(
            package_search_endpoint + "?rows=1000&start={}".format(start),
            headers=headers,
        )
        if count == 1:
            count = get_req.json()["result"]["count"]
        packages = packages + get_req.json()["result"]["results"]
        start = start + 1000
    return packages


packages = get_some_packages()

stamp = datetime.now().strftime("%Y-%m-%d - %H-%M")
with open("packages-" + stamp + ".json", "w") as outfile:
    json.dump(packages, outfile)


package_create_endpoint = "{}/api/action/package_create".format(localhost_url)
resource_create_endpoint = "{}/api/action/resource_create".format(localhost_url)
resource_patch_endpoint = "{}/api/action/resource_patch".format(localhost_url)
resource_query_endpoint = "{}/api/3/action/datastore_search".format(localhost_url)


all_orgs = {}


def get_org_id(org_name):
    if org_name in all_orgs:
        return all_orgs[org_name]

    org_id = None
    req_org = requests.get(
        "{}/api/3/action/organization_show?id={}".format(localhost_url, org_name),
        headers=headers,
    )
    if req_org.json()["success"]:
        org_id = req_org.json()["result"]["id"]

    else:
        # Create missing organization to get ID.
        req_org_from_production = requests.post(
            "{}/api/3/action/organization_show?id={}".format(site_url, org_name),
            headers=headers,
        )
        org_json = req_org_from_production.json()["result"]
        del org_json["id"]

        req_org = requests.post(
            "{}/api/3/action/organization_create".format(localhost_url),
            json=org_json,
            headers=localhost_headers,
        )
        org_id = req_org.json()["result"]["id"]
    all_orgs[org_name] = org_id
    return org_id


# Remove the attributes that we do not want to pass into the request
def dictFilter(the_attributes, the_dict):
    new_dict = {}
    for key, value in the_dict.items():
        if key in the_attributes:
            new_dict[key] = value

    return new_dict


# Format a dictionary for POST request
def formatForPosting(dictForPosting):
    for key, value in dictForPosting.items():
        if isinstance(value, dict):
            dictForPosting[key] = json.dumps(value)

    return dictForPosting


with open("packages-" + stamp + ".json") as file:
    packages = json.load(file)
    for package in packages:
        if package["name"] in white_list:
            org_id = get_org_id(package["organization"]["name"])
            package["owner_org"] = org_id
            resources = []
            resources = package["resources"]
            to_delete = [
                "id",
                "resources",
                "license_title",
                "num_tags",
                "metadata_created",
                "metadata_modified",
                "relationships_as_subject",
                "num_resources",
                "tags",
                "groups",
                "creator_user_id",
            ]
            for field in to_delete:
                del package[field]
            req = requests.post(
                package_create_endpoint, json=package, headers=localhost_headers
            )

            logging.info("%s", package["name"])
            logging.info("%s %s", req.status_code, req.reason)
            if not req.status_code == 200:
                print(package["name"] + " package not patched.")
            else:
                print(package["name"] + " package updated.")
                package_id = req.json()["result"]["id"]
                for r in resources:
                    original_resource_id = r["id"]
                    del r["id"]
                    del r["package_id"]

                    r["package_id"] = package_id
                    resource_file_name = os.path.basename(r["url"])
                    write_path = (
                        "uploads/" + package["name"] + "/" + original_resource_id
                    )
                    if os.path.isdir("uploads") is False:
                        os.mkdir("uploads")
                    if os.path.isdir("uploads/" + package["name"]) is False:
                        os.mkdir("uploads/" + package["name"])
                    if os.path.isdir(write_path) is False:
                        os.mkdir(write_path)

                    # urllib2.urlretrieve(r['url'], write_path+"/"+
                    # resource_file_name)
                    with open(write_path + "/" + resource_file_name, "wb") as f:
                        f.write(urlopen(r["url"]).read())
                        f.close()
                        del r["url"]
                    payload = dictFilter(resource_attributes, r)
                    payload = formatForPosting(payload)
                    payload["package_id"] = package_id
                    with open(write_path + "/" + resource_file_name, "rb") as output:
                        resp = requests.post(
                            resource_create_endpoint
                            + "?package_id="
                            + payload["package_id"],
                            # json=json.dumps(payload),
                            data=payload,
                            headers=localhost_headers,
                            files=[("upload", output)],
                        )
                        logging.info("%s", resource_file_name)
                        logging.info("%s %s", resp.status_code, resp.reason)

                    """ if resp.status_code == 200:
                        new_resource_id = resp.json()["result"]["id"]
                        payload["id"] = new_resource_id
                        if resource_file_name.find(".csv") != -1:
                            print(resp.json()["success"])
                            if resp.json()["success"] == True:
                                time.sleep(10)
                                file_count = get_file_count(
                                    write_path + "/" + resource_file_name
                                )
                                datastore_loaded = False
                                tries = 0
                                last_count = 0
                                while datastore_loaded is False and tries < 3:
                                    time.sleep(30)  # should be about 4500
                                    response = requests.get(
                                        resource_query_endpoint
                                        + "?resource_id="
                                        + new_resource_id
                                        + "&limit=1"
                                    )
                                    print(response.json())
                                    datastore_count = response.json()["result"]["total"]
                                    print(datastore_count)
                                    print("out of")
                                    print(file_count)
                                    if last_count == datastore_count:
                                        tries = tries + 1
                                    else:
                                        last_count = datastore_count
                                    if file_count == datastore_count:
                                        datastore_loaded = True
                                    if tries == 3:
                                        logging.info(
                                            "%s, %s csv rows are off, moving on.",
                                            package["name"],
                                            resource_file_name,
                                        )
                            else:
                                logging.info(
                                    "%s, %s csv didn't upload properly... fix",
                                    package["name"],
                                    resource_file_name,
                                )

                        payload = dict(payload)
                        payload["description_translated"] = json.dumps(
                            payload["description_translated"]
                        )
                        metadata_resp = requests.post(
                            resource_patch_endpoint + "?id=" + new_resource_id,
                            data=payload,
                            headers=localhost_headers,
                        )
                        logging.info("%s", resource_file_name)
                        logging.info(
                            "%s %s", metadata_resp.status_code, metadata_resp.reason
                        )
                    else:
                        logging.info("%s file not uploaded", resource_file_name) """

                    time.sleep(20)
