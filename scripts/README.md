# Installation Scripts

Bash scripts to install Ontario ckan 2.9 and Solr 8.11.2 on separate Ubuntu 20.04 virtual machines.

## Solr

Bash script: `setup_solr.sh`  
Version: Solr 8.11.2

The bash script requires the `managed-schema` config file customized for Ontario ckan, stored in the `config/solr` directory of this repository. This config file is obtained in the script by copying the file from `config/solr` into the Solr config folder `/opt/solr/server/solr/configsets/_default/`.

Note that the bash script installs Solr but does not rebuild the index: this must be done on the machine running CKAN.

### Running the script

1. Export your sudo password as an environment variable named `SUDOPASS`:
```
export SUDOPASS='xxxx'
```

2. Install git, clone this repository, fetch the `ckan_2.9_upgrade` branch, change to the scripts directory, and run the script:
```
echo $SUDOPASS | sudo -S -k apt-get update
{ echo $SUDOPASS; echo 'Y'; } | sudo -S -k apt-get install git
git clone https://github.com/ongov/ckanext-ontario_theme.git
cd ckanext-ontario_theme

git fetch origin ckan_2.9_upgrade:ckan_2.9_upgrade
git checkout ckan_2.9_upgrade

cd scripts
./setup_solr.sh
```

Note: After the tar file is extracted, there will be a message:
`[sudo] password for ckan29: id: ‘solr’: no such user`. This is normal and can be ignored.

3. Unset the SUDOPASS environment variable:
```
unset SUDOPASS
```
### Check status  
Check the success of the installation on the command line and/or the browser.

**Command line:**  
- check that response status is 200:
```
$ curl -s -o /dev/null -I -w '%{http_code}' http://{ip_address}:8983/solr/admin/cores?action=STATUS

200
```
- check that the Solr node is found:
```
$ sudo /etc/init.d/solr status

Found 1 Solr nodes:
```
- check that Solr service is running:
```
$ sudo service solr status

solr.service - LSB: Controls Apache Solr as a Service
     Loaded: loaded (/etc/init.d/solr; generated)
     Active: active (exited) 
```

**Browser:**  
Check that Solr is running on `http://127.0.0.1:8983/solr/`. The ckan core should be listed in the Core Admin menu with `instanceDir /var/solr/data/ckan`.

You can also check that the schema properties reflect the Ontario theme. In the Core Selector dropdown menu, choose ckan, and then select Schema from the menu. The Unique Key Field should be `index_id`.

![image](https://user-images.githubusercontent.com/1254764/167931044-3bb4686a-eebd-4651-92ce-b6a82cb0309f.png)


# Load Organization Data Script

This script (`load_organization_data.py`) allows you to load organization data into your application using the CKAN API. Before running the script, please ensure that you have the necessary prerequisites and follow the instructions below.

## Prerequisites

- Python (version 3.x)
- Requests library (can be installed via `pip install requests`)

## Setup

1. Clone the repository containing the script:

2. Install the required dependencies by navigating to the repository directory and running:

     pip install -r requirements.txt


## Configuration

1. Obtain an API key from your CKAN application. You can find the API key in the CKAN user settings at `http://localhost/user/edit/admin`. Make sure you are logged in as an administrator.

2. Open the `load_organization_data.py` script in a text editor.

3. Locate the `api_token` variable in the script and replace the empty string `""` with your obtained API key:
```python
api_token = "your_api_key_here"


## Usage 

Ensure that your CKAN application is running locally at http://localhost.

Place the CSV files containing organization data in the uploads directory within the repository.

Open a terminal or command prompt and navigate to the repository directory.

Run the script using the following command:

python scripts/load_organization_data.py


The script will process the CSV files and create organizations in your CKAN application. Any resources associated with the organizations will be uploaded and attached to the respective organizations.

Monitor the script's output and check for any error messages or failed resource uploads.

Once the script completes, verify that the organizations and their associated resources have been successfully created in your CKAN application.

## Additional Notes
The script expects the CSV files to be present in the uploads directory. Ensure that the CSV files follow the required format and contain the necessary data for creating organizations and resources.

If any errors occur during resource uploads, review the error messages and the failed_resource_writes list in the script's output. You may need to investigate and address any issues with the resource files or network connectivity.

You can customize the script further to accommodate specific requirements or modify the behavior as needed.


