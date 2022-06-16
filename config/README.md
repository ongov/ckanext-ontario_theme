# Configuration Files

This folder contains configuration files for the following applications:

| Application | Version     |Config file |
| ----------- | ----------- |----------- |
| NGINX (prod)| nginx/1.18.0 (Ubuntu)    |[ckan](https://github.com/ongov/ckanext-ontario_theme/blob/ckan_2.9_upgrade/config/nginx/ckan)|
| NGINX (local prod)| nginx/1.18.0 (Ubuntu)    |[localckan](https://github.com/ongov/ckanext-ontario_theme/blob/localckan_script/config/nginx/localckan)|
| uWSGI       |     |[ckan-uwsgi.conf](https://github.com/ongov/ckanext-ontario_theme/blob/ckan_2.9_upgrade/config/uwsgi/ckan-uwsgi.conf)|
| Solr        | 8.11.1      |[managed-schema](https://github.com/ongov/ckanext-ontario_theme/blob/ckan_2.9_upgrade/config/solr/managed-schema)|

## NGINX
The default config file [ckan](https://github.com/ongov/ckanext-ontario_theme/blob/ckan_2.9_upgrade/config/nginx/ckan) for a production server was copied from the CKAN documentation for [deploying a source install](https://docs.ckan.org/en/2.9/maintaining/installing/deployment.html#create-the-nginx-config-file) for production. This config file is retrieved when the `ckan_install.sh` script is run.

Use the config file [localckan](https://github.com/ongov/ckanext-ontario_theme/blob/localckan_script/config/nginx/localckan) to run CKAN on a local virtual machine in production mode at `https://localhost` instead of `http://localhost`. This config file was modified from the default file by turning on SSL and including the SSL certificates, and is retrieved when the [localprod_ssl.sh](https://github.com/ongov/ckanext-ontario_theme/blob/localckan_script/scripts/localprod_ssl.sh) script is run.

## uWSGI
The [ckan-uwsgi.conf](https://github.com/ongov/ckanext-ontario_theme/blob/ckan_2.9_upgrade/config/uwsgi/ckan-uwsgi.conf) config file was copied from the CKAN documentation for [deploying a source install](https://docs.ckan.org/en/2.9/maintaining/installing/deployment.html#id2) for production. This config file is retrieved when the [ckan_install.sh](https://github.com/ongov/ckanext-ontario_theme/blob/ckan_script/scripts/ckan_install.sh) script is run.


## Solr

The [managed-schema](https://github.com/ongov/ckanext-ontario_theme/blob/ckan_2.9_upgrade/config/solr/managed-schema) config file was originally obtained from the [ckan-solr](https://github.com/ckan/ckan-solr) Docker image (tag `ckan/ckan-solr:2.9-solr8`). It is retrieved by the [setup_solr.sh](https://github.com/ongov/ckanext-ontario_theme/blob/solr8/scripts/setup_solr.sh) bash script for setting up Solr and contains the following modifications for the Ontario theme:
```
<!-- Extra Ontario fields -->
<field name="keywords_en" type="string" indexed="true" stored="true" multiValued="true"/>
<field name="keywords_fr" type="string" indexed="true" stored="true" multiValued="true"/>

```
