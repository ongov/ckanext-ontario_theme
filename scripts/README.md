# Installation Scripts Guide

Bash scripts to install CKAN 2.9 compliant Ontario Theme, and Solr 8.11.2 on a separate Ubuntu 20.04 virtual machine. The objective of the scripts is to create a local dev-test environment.

During the course of the script execution, the code repository will be cloned into `/usr/lib/ckan/default/src` for installation. This cloned directory in `/usr/lib/ckan/default/src` is independent of the code used for installation purposes. `/usr/lib/ckan/default/src` is the directory where the code changes need to be made for dev work.

### Common Steps

The installation includes some common steps that are aggregated here. They mentioned in the instructions whenever their execution is needed

1. Export your sudo password as an environment variable named `SUDOPASS`:

```bash
export SUDOPASS='xxxx'
```

2. Install git

```bash
echo $SUDOPASS | sudo -S -k apt-get -y install git
```

3. Clone this repository

```bash
git clone https://github.com/ongov/ckanext-ontario_theme.git
```

4. change to the scripts directory

```bash
cd ckanext-ontario_theme/scripts
```

## Solr Installation

Bash script: `setup_solr.sh`
Version: Solr 8.11.2

This script requires the `managed-schema` config file, customized for Ontario CKAN. This config file is stored in the `config/solr` directory of this repository and copied into the Solr config folder (`/opt/solr/server/solr/configsets/_default/`) during the script execution.

Take note, this script handles Solr installation, but does not rebuild the index. You must perform this step on the machine where CKAN is running.

### Script Execution Steps

1. Do the steps common to the scripts in [common steps](#common-steps)
2. run the `setup_solr.sh` script:

```bash
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

## CKAN & Ontario Theme

Bash script: `setup_ckan_local.sh`

This bash script installs CKAN and Ontario Theme locally, preferably on a Virutal Machine. The script follow the steps from the [official installation guide for installing CKAN from source](https://docs.ckan.org/en/2.9/maintaining/installing/install-from-source.htmlhttps:/).

### Developer and Production Modes

CKAN can be installed in Developer Mode, where the CKAN server is started manually through the commandline (`$ ckan -c /etc/ckan/default/ckan.ini run `) and is available at `localhost:5000` in the browser; Or CKAN can be installed in Production Mode where `supervisor` application is responsible for running the CKAN application and `nginx` is used as the webserver available directly at `localhost` in the browser. The Production Mode is how CKAN runs in production environment.

The script installs CKAN+Ontario Theme in Production Mode.

### What does the Script need?

The script needs Solr, postgreSQL and relevant databases to be setup. These steps are recorded in the instructions below.

For configuration, files in `config/` directory are used.

* `config/ckan/ckan.ini` file is copied to`/etc/ckan/default/ckan.ini`, and modified during the course of execution of the script
* `config/gtm/gtm.html` and `config/gtm/gtm_ns.html` are copied to `/usr/lib/ckan/default/src/ckanext-ontario_theme/ckanext/ontario_theme/templates/internal/`
* `config/nginx/local_ckan_ssl` is copied to `/etc/nginx/sites-available/`
* `config/supervisor/ckan-uwsgi.conf` and `config/supervisor/ckan-worker.conf` are copied to `/etc/supervisor/conf.d/`

### Running the script

**Command line:**

1. Do the steps common to the scripts in [common steps](#common-steps)

2. Setup Solr8 locally as described in [Solr Installation](#solr-installation)

3. Export your sudo password as an environment variable named `SUDOPASS`:

```bash
export SUDOPASS='xxxx'
```

4. Setup PostgreSQL locally

```bash
sudo bash setup_postgres_local.sh
```

5. run script to install ckan

```bash
bash setup_ckan_local.sh
```

6. Rebuild SOLR search index

```bash
. /usr/lib/ckan/default/bin/activate
 ckan -c /etc/ckan/default/ckan.ini search-index rebuild
```

7. Unset the SUDOPASS environment variable:

```bash
unset SUDOPASS
```

**Browser:**
Check ckan status by going to `localhost` in a browser

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
4. Run the `load_organization_data.py` script.


### Known Issues
**Script Doesn't Run (load_organization_data.py)**
If the script starts to run, but throws `simplejson.errors.JSONDecodeError` it might be because you're not connected to VPN. Try connecting to your VPN connection and rerunning the script. 

**Storage Issues (M1)**
If you receive a message about not having enough disk space left while running the load_organization_data.py script or during any of the other steps, follow the troublshooting steps in the links below to regain some space.

https://github.com/utmapp/UTM/issues/2636#issuecomment-1290021310

https://linux.afnom.net/install_apple/apple_silicon.html

Breakdown of the steps:

1. Delete some data from the VM, so you have around 1GB of free space.
2. Use df -h to check if there's free space.
3. On the VM, install gparted software.
```
   sudo apt-get install gparted -y
```
4. Start gparted. gparted is a linux disk management utility. What you will see is that the disk is 10GB but it can be expanded to 40GB and that space is not occupied. Extend your disk to 40GB and apply the settings.
5. The VM will reboot, and your Ubuntu disk will now be 40GB.
6. You can now run the data loading scripts.
