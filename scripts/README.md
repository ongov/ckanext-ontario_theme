# Installation Scripts

Bash scripts to install Ontario ckan 2.9 and Solr 8.11.1 on separate Ubuntu 20.04 virtual machines.

## Solr

Script: `setup_solr.sh`
Version: Solr 8.11.1

The bash script requires the `managed-schema` config file customized for Ontario ckan, stored in the `config/solr` of this repository. This config file is obtained in the script by copying the file from `config/solr` into the Solr config folder `/opt/solr/server/solr/configsets/_default/`.

Note that the bash script installs Solr but does not rebuild the index: this must be done on the ckan machine.

### Running the script

1. Export your sudo password as an environment variable named `SUDOPASS`:
```
$ export SUDOPASS='xxxx'
```

2. Install git, clone this repository, fetch the `solr8` branch, change to the scripts directory, and run the script:
```
$ sudo apt-get update
$ sudo apt-get install git
$ git clone https://github.com/ongov/ckanext-ontario_theme.git
$ cd ckanext-ontario_theme
$ git fetch origin solr8:solr8
$ cd scripts
$ ./setup_solr
```

3. Unset the SUDOPASS environment variable:
```
$ unset SUDOPASS
```
