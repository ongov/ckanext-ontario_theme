#! /bin/bash
source ./helper_functions.sh

export SUDOPASS='1'
export POSTGRESSERVER="localhost"
export POSTGRESSERVERURL="localhost"
export POSTGRESSERVERPORT="5432"
export CKANINIPATH="/etc/ckan/default/ckan.ini"
export CKANUSER='ckan_default'
export CKANPASS='ckan_default'
export CKANDB='ckan_default'
export CKANURL='localhost'
export CKANPORT='5000'
export DATASTOREUSER='datastore_default'
export DATASTOREPASS='datastore_default'
export DATASTOREDB='datastore_default'
export SOLRURL='http://127.0.0.1'
export SOLRPORT='8983'
export XLOADER_REQ_VER='0.9.0'

# echo $SUDOPASS | sudo -S -k apt-get install -y git git-core

# Install Dependencies
echo "Installing packages..."
echo $SUDOPASS | sudo -S -k apt-get update
echo $SUDOPASS | sudo -S -k apt-get install -y redis-server python3-pip python3-virtualenv python3-dev python3.8-venv libpq-dev

# Install CKAN into py virt env
echo $SUDOPASS | sudo -S -k mkdir -p /usr/lib/ckan/default
echo $SUDOPASS | sudo -S -k chown `whoami` /usr/lib/ckan/default
python3 -m venv /usr/lib/ckan/default
. /usr/lib/ckan/default/bin/activate

# install tools and ckan
pip3 install setuptools==45 wheel==0.37.1
pip3 install -e 'git+https://github.com/ckan/ckan.git@ckan-2.9.5#egg=ckan[requirements]'

echo $SUDOPASS | sudo -S -k mkdir -p /etc/ckan/default
echo $SUDOPASS | sudo -S -k chown -R `whoami` /etc/ckan/

# Copying and Configuring ckan.ini to /etc/ckan/default/
cp `pwd`/../config/ckan/ckan.ini /etc/ckan/default/

# sqlalchemy.url
SQLALCHEMY_STRING=`str_to_sed_str "sqlalchemy.url = postgresql://ckan_default:pass@localhost/ckan_default"`
SQLALCHEMY_REPLACEMENT_STRING=`str_to_sed_str "sqlalchemy.url = postgresql://$CKANUSER@$POSTGRESSERVER:$CKANPASS@$POSTGESSERVERURL:$POSTGRESSERVERPORT/$CKANDB?sslmode=require"`

sed -i -r 's/'"$SQLALCHEMY_STRING"'/'"$SQLALCHEMY_REPLACEMENT_STRING"'/' $CKANINIPATH

# ckan.site_url
CKANSITE_URL_STRING=`str_to_sed_str "ckan.site_url = http://localhost:5000"`
CKANSITE_URL_REPLACEMENT_STRING=`str_to_sed_str "ckan.site_url = http://$CKANURL:$CKANPORT"`

sed -i -r 's/'"$CKANSITE_URL_STRING"'/'"$CKANSITE_URL_REPLACEMENT_STRING"'/' $CKANINIPATH

echo "ckan installed successfully."

# solr_url
SOLR_URL_STRING=`str_to_sed_str "solr_url = http://127.0.0.1:8983/solr/ckan"`
SOLR_URL_REPLACEMENT_STRING=`str_to_sed_str "solr_url = $SOLRURL:$SOLRPORT/solr/ckan"`

sed -i -r 's/'"$SOLR_URL_STRING"'/'"$SOLR_URL_REPLACEMENT_STRING"'/' $CKANINIPATH

echo "solr connected successfully."

# Link to who.ini
ln -s /usr/lib/ckan/default/src/ckan/who.ini /etc/ckan/default/who.ini

# setup filestore & ckan admin account
ckan -c /etc/ckan/default/ckan.ini sysadmin add admin email=admin@localhost name=admin
echo $SUDOPASS | sudo -S -k chown -R `whoami` /usr/lib/ckan/default
echo $SUDOPASS | sudo -S -k chmod -R u+rw /usr/lib/ckan/default

# datastore
# update datastore in ckan.ini
DATASTORE_WRITE_URL="ckan.datastore.write_url = postgresql://ckan_default:pass@localhost/datastore_default"
DATASTORE_WRITE_URL_REPLACEMENT="ckan.datastore.write_url = postgresql://$CKANUSER@$POSTGRESSERVER:$CKANPASS@$POSTGESSERVERURL:$POSTGRESSERVERPORT/$DATASTOREDB?sslmode=require"
replace_string_in_ckan_ini $DATASTORE_WRITE_URL $DATASTORE_WRITE_URL_REPLACEMENT

DATASTORE_READ_URL="ckan.datastore.read_url = postgresql://datastore_default:pass@localhost/datastore_def"
DATASTORE_READ_URL_REPLACEMENT="ckan.datastore.write_url = \postgresql://$DATASTOREUSER@$POSTGRESSERVER:$DATASTOREPASS@$POSTGESSERVERURL:$POSTGRESSERVERPORT/$DATASTOREDB?sslmode=require"
replace_string_in_ckan_ini $DATASTORE_READ_URL $DATASTORE_READ_URL_REPLACEMENT

# datastore permissions

# echo $SUDOPASS | sudo -S -k && ckan -c /etc/ckan/default/ckan.ini datastore set-permissions | sudo -u postgres psql --set ON_ERROR_STOP=1
{ echo $SUDOPASS; ckan -c /etc/ckan/default/ckan.ini datastore set-permissions; } | sudo -u postgres psql --set ON_ERROR_STOP=1

echo "datastore enabled successfully."

# xloader
# update xloader in ckan.ini
XLOADER_URI="ckanext.xloader.jobs_db.uri = postgresql://ckan_default:pass@localhost/ckan_default"
XLOADER_URI_REPLACEMENT="ckan.datastore.write_url = postgresql://$CKANUSER@$POSTGRESSERVER:$CKANPASS@$POSTGESSERVERURL:$POSTGRESSERVERPORT/$CKANDB?sslmode=require"
replace_string_in_ckan_ini $XLOADER_URI $XLOADER_URI_REPLACEMENT
# clone and install
cd usr/lib/ckan/default/src
git clone http://github.com/ckan/ckanext-xloader.git
cd ckanext-xloader
python3 setup.py develop
pip3 install -r requirements.txt
pip3 install -r dev-requirements.txt
# verify version
XLOADER_INSTALLED_VER=`pip3 list | grep xloader`
if [[ $XLOADER_INSTALLED_VER == *$XLOADER_REQ_VER* ]]; then
  echo "xloader installed successfully."
else
  echo "incorrect xloader version $XLOADER_INSTALLED_VER";
fi
