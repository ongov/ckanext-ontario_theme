====================
Installation Scripts
====================

Bash scripts to install Ontario ckan 2.9 and Solr 8.11.1 on separate Ubuntu 20.04 virtual machines.

------------
Solr
------------

Script: ``setup_solr.sh``    
Version: Solr 8.11.1

The bash script requires the ``managed-schema`` config file customized for Ontario ckan, stored in ``config/solr``. This config file is obtained in the script by cloning this repository and copying the file into the Solr config folder ``/opt/solr/server/solr/configsets/_default/``.

Note that the bash script installs Solr but does not rebuild the index: this must be done on the ckan machine.

