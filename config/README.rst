====================
Configuration Files
====================

Configuration files for:  

* Solr 

.. list-table:: Details: 
 :header-rows: 1

 * - Application
   - Version 
   - Config file
 * - Solr
   - 8.11.2
   - ``managed-schema``

* CKAN
.. list-table:: Details: 
 :header-rows: 1

 * - Application
   - Version 
   - Config file
 * - CKAN
   - 2.9.5
   - ``ckan.ini``
* Nginx
.. list-table:: Details: 
 :header-rows: 1

 * - Application
   - Version 
   - Config file
 * - Nginx
   - 1.18.0
   - ``local_ckan_ssl``
* Supervisord
.. list-table:: Details: 
 :header-rows: 1

 * - Application
   - Version 
   - Config file
 * - Supervisord
   - 4.1.0
   - ``ckan.ini``


------------
Solr
------------

The ``managed-schema`` config file was originally obtained from the `ckan-solr <https://github.com/ckan/ckan-solr>`_ Docker image (tag ``ckan/ckan-solr:2.9-solr8``). This file was then modified for Ontario ckan by including the following multi-valued fields:

    <!-- Extra Ontario fields -->

    <field name="keywords_en" type="string" indexed="true" stored="true" multiValued="true"/>

    <field name="keywords_fr" type="string" indexed="true" stored="true" multiValued="true"/>

The ``managed-schema`` config file is fetched in the `setup_solr.sh <https://github.com/ongov/ckanext-ontario_theme/blob/ckan_script/scripts/setup_solr.sh>`_ bash script for setting up Solr.   

------------
CKAN
------------
The ``ckan.ini`` file is a modified ckan configuration file that is needed to run ckan locally.
``ckan.ini`` is fetched/modified by `ckan_local_install.sh <https://github.com/ongov/ckanext-ontario_theme/blob/ckan_script/scripts/ckan_local_install.sh>` and `ckan_localprod_install.sh <https://github.com/ongov/ckanext-ontario_theme/blob/ckan_script/scripts/ckan_localprod_install.sh>` for setting up ckan.

------------
Nginx
------------
``local_ckan_ssl`` is the nginx config file used to configure nginx to support local production (with certificate) deployment of ckan.
`ckan_localprod_install.sh <https://github.com/ongov/ckanext-ontario_theme/blob/ckan_script/scripts/ckan_localprod_install.sh>` uses ``local_ckan_ssl`` to setup nginx. ``local_ckan`` file is not used and is kept for reference.

------------
Supervisord
------------
``ckan-uwsgi.conf`` file has configuration for uwsgi server management using supervisord.
`ckan_localprod_install.sh <https://github.com/ongov/ckanext-ontario_theme/blob/ckan_script/scripts/ckan_localprod_install.sh>` uses ``ckan-uwsgi.conf`` when doing local production deployment of ckan.
