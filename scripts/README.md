# Installation Scripts

Bash scripts to install Ontario ckan 2.9 and Solr 8.11.1 on separate Ubuntu 20.04 virtual machines.

## Solr

Bash script: `setup_solr.sh`  
Version: Solr 8.11.1

The bash script requires the `managed-schema` config file customized for Ontario ckan, stored in the `config/solr` directory of this repository. This config file is obtained in the script by copying the file from `config/solr` into the Solr config folder `/opt/solr/server/solr/configsets/_default/`.

Note that the bash script installs Solr but does not rebuild the index: this must be done on the machine running CKAN.

### Running the script

1. Export your sudo password as an environment variable named `SUDOPASS`:
```
export SUDOPASS='xxxx'
```

2. Install git, clone this repository, fetch the `solr8` branch, change to the scripts directory, and run the script:
```
echo $SUDOPASS | sudo -S -k apt-get update
echo $SUDOPASS | sudo -S -k apt-get install git
git clone https://github.com/ongov/ckanext-ontario_theme.git
cd ckanext-ontario_theme
git fetch origin solr8:solr8
git checkout solr8
cd scripts
./setup_solr.sh
```

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
