# Installation Scripts Guide

This document provides instructions for using bash scripts to install Ontario CKAN 2.9 and Solr 8.11.2 on individual Ubuntu 20.04 virtual machines.

## Solr Installation

### Bash Script Information
- Filename: `setup_solr.sh`
- Version: Solr 8.11.2

This script requires the `managed-schema` config file, customized for Ontario CKAN. This config file is stored in the `config/solr` directory of this repository and copied into the Solr config folder (`/opt/solr/server/solr/configsets/_default/`) during the script execution.

Take note, this script handles Solr installation, but does not rebuild the index. You must perform this step on the machine where CKAN is running.

### Script Execution Steps

**Step 1:** Export your sudo password as an environment variable, `SUDOPASS`. Example command:
```
export SUDOPASS='your_sudo_password'
```

**Step 2:** Install Git, clone the repository, fetch the `ckan_2.9_upgrade` branch, switch to the scripts directory, and execute the script. Follow the commands below:

```bash
# Update packages
echo $SUDOPASS | sudo -S -k apt-get update

# Install Git
{ echo $SUDOPASS; echo 'Y'; } | sudo -S -k apt-get install git

# Clone the repository
git clone https://github.com/ongov/ckanext-ontario_theme.git
cd ckanext-ontario_theme

# Navigate to the scripts directory and execute the setup script
cd scripts
./setup_solr.sh
```

Note: You may see a message stating `[sudo] password for ckan29: id: ‘solr’: no such user` after the tar file extraction. This is expected and you can ignore it.

**Step 3:** Unset the `SUDOPASS` environment variable with the following command:
```
unset SUDOPASS
```

### Checking Solr Status
You can verify the installation success via command line or a browser.

- **Command Line Checks:**  
   - Confirm response status is 200:  
     ```
     curl -s -o /dev/null -I -w '%{http_code}' http://{ip_address}:8983/solr/admin/cores?action=STATUS
     ```
   - Verify Solr node is found:  
     ```
     sudo /etc/init.d/solr status
     ```
   - Check Solr service is running:  
     ```
     sudo service solr status
     ```

- **Browser Checks:**  
   - Visit `http://127.0.0.1:8983/solr/` to see if Solr is running.
   - Check the Core Admin menu for the CKAN core with `instanceDir /var/solr/data/ckan`.
   - Verify that the schema properties reflect the Ontario theme (Unique Key Field should be `index_id`).

## Organization Data Script

The `load_organization_data.py` script enables you to load organization data into your application via the CKAN API. Please fulfill the necessary prerequisites and follow the given instructions before running the script.

### Prerequisites
- Python 3.x
- Requests library (install via `pip install requests`)

### Script Setup
1. Clone the repository containing the script.
2. Navigate to the repository directory and install the required dependencies by running:
```
pip install -r requirements.txt
```

### Script Configuration
1. Obtain an API key from your CKAN application. You can find this key in the CKAN user settings at `http://localhost/user/edit/admin`. Make sure you're logged in as an administrator.
2. Open the `load_organization_data.py` script in a text editor.
3. Find the `api_token` variable in the script and replace the empty string with your API key:
```python

api_token = "your_api_key_here"

```

### Usage 
Run the script after ensuring your CKAN application is running locally at `http://localhost`. The script will download CSV files.

1. Open a terminal and navigate to the repository directory.
2. Execute the script with the following command:
```
$ python scripts/load_organization_data.py

```

The script processes the CSV files and creates organizations in your CKAN application. It also uploads and attaches any resources associated with the organizations. 

Monitor the script output for any error messages or failed resource uploads. After completion, check if the organizations and their associated resources were created successfully in your CKAN application.

### Additional Notes
The script expects the CSV files to be in the uploads directory. Ensure that the CSV files follow the correct format and contain the necessary data for creating organizations and resources.

If any errors occur during resource uploads, review the error messages and the `failed_resource_writes` list in the script output. Address any issues related to resource files or network connectivity. 

You may modify the script further to meet specific requirements or change its behavior as needed.
