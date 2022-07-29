# Configuration Files

This folder contains configuration files for the following applications:

| Application | Version | Config file |
| ----------- | ------- |------------ |
| Nginx       | 1.18.0 |`ckan`|
| Supervisord | 4.1.0  |`ckan-uwsgi.conf`|
| Solr        | 8.11.1 |`managed-schema`|
| CKAN        | 2.9.5  |`ckan.ini`|

## nginx
The `ckan` config file was copied from the CKAN documentation for [deploying a source install](https://docs.ckan.org/en/2.9/maintaining/installing/deployment.html#create-the-nginx-config-file) for production. This config file is retrieved when the `ckan_install.sh` script is run.

## uwsgi
The `ckan-uwsgi` config file was copied from the CKAN documentation for [deploying a source install](https://docs.ckan.org/en/2.9/maintaining/installing/deployment.html#id2) for production. This config file is retrieved when the `ckan_install.sh` script is run.


## Solr

The `managed-schema` config file was originally obtained from the [ckan-solr](https://github.com/ckan/ckan-solr) Docker image (tag `ckan/ckan-solr:2.9-solr8`). This file was then modified for Ontario ckan by including the following multi-valued fields:
```
<!-- Extra Ontario fields -->
<field name="keywords_en" type="string" indexed="true" stored="true" multiValued="true"/>
<field name="keywords_fr" type="string" indexed="true" stored="true" multiValued="true"/>

```

The `managed-schema` config file is retrieved by the [setup_solr.sh](https://github.com/ongov/ckanext-ontario_theme/blob/solr8/scripts/setup_solr.sh) bash script for setting up Solr.   

## CKAN
The `ckan.ini` file is a modified ckan configuration file that is needed to run ckan locally.
`ckan.ini` is fetched/modified by [ckan_local_install.sh](https://github.com/ongov/ckanext-ontario_theme/blob/ckan_script/scripts/ckan_local_install.sh) and [ckan_localprod_install.sh](https://github.com/ongov/ckanext-ontario_theme/blob/ckan_script/scripts/ckan_localprod_install.sh) for setting up ckan.

## Nginx
`local_ckan_ssl` is the nginx config file used to configure nginx to support local production (with certificate) deployment of ckan. This config file was copied from the CKAN documentation for [deploying a source install](https://docs.ckan.org/en/2.9/maintaining/installing/deployment.html#create-the-nginx-config-file) for production.
[ckan_localprod_install.sh](https://github.com/ongov/ckanext-ontario_theme/blob/ckan_script/scripts/ckan_localprod_install.sh) uses `local_ckan_ssl` to setup nginx. `local_ckan` file is not used and is kept for reference.

## Supervisord
`ckan-uwsgi.conf` file has configuration for uwsgi server management using supervisord. The config file was copied from the CKAN documentation for [deploying a source install](https://docs.ckan.org/en/2.9/maintaining/installing/deployment.html#id2) for production.
[ckan_localprod_install.sh](https://github.com/ongov/ckanext-ontario_theme/blob/ckan_script/scripts/ckan_localprod_install.sh) uses `ckan-uwsgi.conf` when doing local production deployment of ckan.
