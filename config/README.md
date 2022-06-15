# Configuration Files

This folder contains configuration files for the following applications:

| Application | Version     |Config file |
| ----------- | ----------- |----------- |
| nginx       | nginx/1.18.0 (Ubuntu)    |`ckan`|
| uswgi       |     |`ckan-uwsgi.conf`|
| Solr        | 8.11.1      |`managed-schema`|

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

