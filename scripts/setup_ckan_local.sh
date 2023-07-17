#! /bin/bash
source ./helper_functions.sh

#export SUDOPASS='1'
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
export XLOADER_REQ_VER='1.0.1'

CKAN_ONT_THEME_ROOT="`pwd`/.."
CKAN_EXT_ROOT="/usr/lib/ckan/default/src"
GTM_PATH=$CKAN_EXT_ROOT"/ckanext-ontario_theme/ckanext/ontario_theme/templates/internal"

# Install CKAN Dependencies
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
pip3 install -e 'git+https://github.com/ckan/ckan.git@ckan-2.9.7#egg=ckan[requirements]'

echo $SUDOPASS | sudo -S -k mkdir -p /etc/ckan/default
echo $SUDOPASS | sudo -S -k chown -R `whoami` /etc/ckan/

# Copying and Configuring ckan.ini to /etc/ckan/default/
cp $CKAN_ONT_THEME_ROOT/config/ckan/ckan.ini $CKANINIPATH

# sqlalchemy.url
SQLALCHEMY_STRING=`str_to_sed_str "sqlalchemy.url = postgresql://ckan_default:pass@localhost/ckan_default"`
SQLALCHEMY_REPLACEMENT_STRING=`str_to_sed_str "sqlalchemy.url = postgresql://$CKANUSER:$CKANPASS@$POSTGRESSERVERURL:$POSTGRESSERVERPORT/$CKANDB?sslmode=require"`

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

# setup filestore
# ckan.storage_path is already enabled and set to /var/lib/ckan/default
echo $SUDOPASS | sudo -S -k mkdir -p /var/lib/ckan/default
echo $SUDOPASS | sudo -S -k chown -R www-data /var/lib/ckan/default
echo $SUDOPASS | sudo -S -k chmod -R 777 /var/lib/ckan/default # production should use `u+rw`
# enable cached webpages
echo $SUDOPASS | sudo -S -k mkdir -p /usr/lib/ckan/default/src/ckan/ckan/public
echo $SUDOPASS | sudo -S -k chown -R www-data:www-data /usr/lib/ckan/default/src/ckan/ckan/public

# for local, create data tables
ckan -c /etc/ckan/default/ckan.ini db init
echo $SUDOPASS | sudo -S -k -u postgres psql -c "SELECT table_name FROM information_schema.tables"

# create ckan admin account
ckan -c /etc/ckan/default/ckan.ini user add admin email=admin@localhost password=admin123
ckan -c /etc/ckan/default/ckan.ini sysadmin add admin

# datastore
# update datastore in ckan.ini
DATASTORE_WRITE_URL="ckan.datastore.write_url = postgresql://ckan_default:pass@localhost/datastore_default"
DATASTORE_WRITE_URL_REPLACEMENT="ckan.datastore.write_url = postgresql://$CKANUSER:$CKANPASS@$POSTGRESSERVERURL:$POSTGRESSERVERPORT/$DATASTOREDB?sslmode=require"
replace_str_in_ckan_ini "$DATASTORE_WRITE_URL" "$DATASTORE_WRITE_URL_REPLACEMENT"

DATASTORE_READ_URL="ckan.datastore.read_url = postgresql://datastore_default:pass@localhost/datastore_default"
DATASTORE_READ_URL_REPLACEMENT="ckan.datastore.read_url = postgresql://$DATASTOREUSER:$DATASTOREPASS@$POSTGRESSERVERURL:$POSTGRESSERVERPORT/$DATASTOREDB?sslmode=require"
replace_str_in_ckan_ini "$DATASTORE_READ_URL" "$DATASTORE_READ_URL_REPLACEMENT"

# datastore permissions
{ echo $SUDOPASS; ckan -c /etc/ckan/default/ckan.ini datastore set-permissions; } | sudo -S -k -u postgres psql --set ON_ERROR_STOP=1

echo "datastore enabled successfully."

# xloader
# copy xloader configuration
echo $SUDOPASS | sudo -S -k mkdir /var/log/ckan
echo $SUDOPASS | sudo -S -k cp $CKAN_ONT_THEME_ROOT/config/supervisor/ckan-worker.conf /etc/supervisor/conf.d/ckan-worker.conf
# update xloader settings in ckan.ini
XLOADER_URI="ckanext.xloader.jobs_db.uri = postgresql://ckan_default:pass@localhost/ckan_default"
XLOADER_URI_REPLACEMENT="ckanext.xloader.jobs_db.uri = postgresql://$CKANUSER:$CKANPASS@$POSTGRESSERVERURL:$POSTGRESSERVERPORT/$CKANDB?sslmode=require"
replace_str_in_ckan_ini "$XLOADER_URI" "$XLOADER_URI_REPLACEMENT"
# clone and install
cd /usr/lib/ckan/default/src

git clone --depth 1 --branch $XLOADER_REQ_VER https://github.com/ckan/ckanext-xloader.git
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

# install ckan scheming
pip3 install -e "git+https://github.com/ckan/ckanext-scheming.git#egg=ckanext-scheming"

# install fluent
git clone https://github.com/ckan/ckanext-fluent.git
cd ckanext-fluent
python3 setup.py develop
pip3 install -r requirements.txt

# install ontario theme
cd $CKAN_EXT_ROOT
git clone https://github.com/ongov/ckanext-ontario_theme.git
cd ckanext-ontario_theme
git fetch
git checkout -b ckan_script origin/ckan_script
python3 setup.py develop
pip3 install -r dev-requirements.txt

# copy google tag manager (placeholder) files
cp $CKAN_ONT_THEME_ROOT/config/gtm/* $GTM_PATH/

# update plugins
PLUGINS="ckan.plugins = stats text_view image_view recline_view"
PLUGINS_REPLACEMENT="ckan.plugins = ontario_theme_external ontario_theme scheming_datasets scheming_organizations scheming_groups fluent stats text_view image_view recline_view datastore xloader"
replace_str_in_ckan_ini "$PLUGINS" "$PLUGINS_REPLACEMENT"

# Setuo CKAN Production Mode
export CKANINIROOT="/etc/ckan/default/"

# set permissions for cache dir
echo $SUDOPASS | sudo -S -k chmod -R 777 /tmp/default/*

# uwsgi script & server
echo $SUDOPASS | sudo -S -k cp /usr/lib/ckan/default/src/ckan/wsgi.py /etc/ckan/default/
echo $SUDOPASS | sudo -S -k chown www-data /etc/ckan/default/wsgi.py
echo $SUDOPASS | sudo -S -k chown -R www-data /var/lib/ckan/default/webassets
. /usr/lib/ckan/default/bin/activate
pip3 install -Iv uwsgi==2.0.20
echo $SUDOPASS | sudo -S -k cp /usr/lib/ckan/default/src/ckan/ckan-uwsgi.ini /etc/ckan/default/

# configure supervisor
echo $SUDOPASS | sudo -S -k apt-get -y install supervisor=4.1.0*
echo $SUDOPASS | sudo -S -k cp $CKAN_ONT_THEME_ROOT/config/supervisor/ckan-uwsgi.conf /etc/supervisor/conf.d/ckan-uwsgi.conf

# install and configure nginx
echo $SUDOPASS | sudo -S -k apt-get -y install nginx=1.18.0*
echo $SUDOPASS | sudo -S -k cp $CKAN_ONT_THEME_ROOT/config/nginx/local_ckan_ssl /etc/nginx/sites-available/
echo $SUDOPASS | sudo -S -k ln -s /etc/nginx/sites-available/local_ckan_ssl /etc/nginx/sites-enabled/

# Generate and configure a certificate
# Create SSL certificate
# https://docs.ckan.org/en/2.9/maintaining/configuration.html#ckan-devserver-ssl-cert
SSLNAME=$CKANINIROOT'ckan_host'
openssl genrsa 2048 > $SSLNAME.key
chmod 400 $SSLNAME.key
openssl req -new -x509 -nodes -sha256 -days 3650 -key $SSLNAME.key -subj "/C=CA/ST=ON/L=./O=ODS/OU=./CN=." > $SSLNAME.cert

# Modify site_url in ckan.ini
SITEURL="ckan.site_url = http://localhost:5000"
SITEURL_REPLACEMENT="ckan.site_url = https://localhost"
replace_str_in_ckan_ini "$SITEURL" "$SITEURL_REPLACEMENT"

# Restart NGINX and supervisor
echo $SUDOPASS | sudo -S -k service nginx restart
echo $SUDOPASS | sudo -S -k service supervisor restart
