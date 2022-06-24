#! /bin/bash
source ./helper_functions.sh

export SUDOPASS='1'
export POSTGRESSERVERURL="localhost"
export POSTGRESSERVERPORT="5432"
export CKANINIPATH="/etc/ckan/default/ckan.ini"
export CKANUSER='ckan_default' # ckan_default or ckan_default@ops-postgres-009
export CKANPASS='ckan_default'
export CKANDB='ckan_default'
export CKANURL='localhost'
export CKANPORT='5000'
export DATASTOREUSER='datastore_default' # datastore_default or datastore_default@ops-postgre-009
export DATASTOREPASS='datastore_default'
export DATASTOREDB='datastore_default'
export SOLRURL='http://127.0.0.1'
export SOLRPORT='8983'
export XLOADER_REQ_VER='0.9.0'

export CKAN_VENV='/usr/lib/ckan/default'
cd $CKAN_VENV/src/
. /usr/lib/ckan/default/bin/activate
pip3 install -e "git+https://github.com/ckan/ckanext-scheming.git#egg=ckanext-scheming"