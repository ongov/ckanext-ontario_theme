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

## CKAN+Ontario Theme Local installation in Developer Mode

Bash script: `ckan_local_install.sh`  

This bash script installs CKAN in developer mode locally. It needs Solr, postgreSQL and relevant databases to be setup before being executed. This can be done by installing SOLR and Postgres by running the accompanying scirpts in shell. 
The script also needs a base config `ckan.ini` file. This is copied from `config/ckan` to `/etc/ckan/default/ckan.ini`, and modified during the course of execution of the script

### Running the script

**Command line:**  

1. Export your sudo password as an environment variable named `SUDOPASS`:
```
export SUDOPASS='xxxx'
```

2. setup solr and postgresql
```
bash setup_solr.sh && bash postgres_install.sh && bash create_datatables.sh
```

3. run script to install ckan
```
bash ckan_local_install.sh
```

4. Unset the SUDOPASS environment variable:
```
unset SUDOPASS
```

5. run ckan
```
. /usr/lib/ckan/default/bin/activate
ckan -c /etc/ckan/default/ckan.ini run
```

**Browser:** 
Check ckan status by going to  `http://127.0.0.1:5000` in a browser

## CKAN & Ontario Theme Local installation in Production Mode

Bash script: `ckan_localprod_install.sh`  

This bash script installs CKAN in production mode with SSL Certificates locally. It needs Solr, postgreSQL and relevant databases, ckan and ontario theme to be setup before being executed. This can be done by installing SOLR, Postgres, CKAN and Ontario Theme by running the accompanying scirpts in shell. 
The script also needs a base config `config/nginx/local_ckan_ssl`, and `config/supervisor/ckan-uwsgi.conf` files. These are copied to `/etc/nginx/sites-enabled/` and `/etc/supervisor/conf.d/ckan-uwsgi.conf` respectively.

### Running the script

**Command line:**  

1. Install CKAN & Ontario Theme locally using instructions in [CKAN Local Install](#CKAN-&-Ontario-Theme-Local -nstallation-in-Production-Mode).

2. Apply settings for production environment using the following command
```
bash ckan_localprod_install.sh
```

3. Unset the SUDOPASS environment variable:
```
unset SUDOPASS
```

**Browser:** 
Check ckan status by going to  `https://localhost` in a browser
