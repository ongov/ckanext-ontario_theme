#! /bin/bash

export CKANINIPATH="/etc/ckan/default/ckan.ini"
export SITEURL='ckan.site_url = http'
export SITEURL_REPLACEMENT='ckan.site_url = https'
export SSLNAME='ckan_host'


# Create SSL certificate
# https://docs.ckan.org/en/2.9/maintaining/configuration.html#ckan-devserver-ssl-cert

openssl genrsa 2048 > $SSLNAME.key
chmod 400 $SSLNAME.key
openssl req -new -x509 -nodes -sha256 -days 3650 -key $SSLNAME.key -subj "/C=CA/ST=ON/L=./O=ODS/OU=./CN=." > $SSLNAME.cert

# Retrieve NGINX config file
cp /usr/lib/ckan/default/src/ckanext-ontario_theme/config/nginx/localckan /etc/nginx/sites-available/

# Backup original config file
cd /etc/nginx/sites-available/
cp ckan ckan_orig
mv localckan ckan

# Modify site_url in ckan.ini
sed -i -r 's/'"$SITEURL"'/'"$SITEURL_REPLACEMENT"'/g' $CKANINIPATH

# Restart NGINX and supervisor
echo $SUDOPASS | sudo -S service nginx restart
sudo service supervisor restart
