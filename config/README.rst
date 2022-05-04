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
   - 8.11.1
   - ``managed-schema`` 

------------
Solr
------------

The ``managed-schema`` config file was originally obtained from the `ckan-solr <https://github.com/ckan/ckan-solr>`_ Docker image (tag ``ckan/ckan-solr:2.9-solr8``). This file was then modified for Ontario ckan by including the following multi-valued fields:

    <!-- Extra Ontario fields -->

    <field name="keywords_en" type="string" indexed="true" stored="true" multiValued="true"/>

    <field name="keywords_fr" type="string" indexed="true" stored="true" multiValued="true"/>

The ``managed-schema`` config file is fetched in the `setup_solr.sh <https://github.com/ongov/ckanext-ontario_theme/blob/solr8/scripts/setup_solr.sh>`_ bash script for setting up Solr.   

