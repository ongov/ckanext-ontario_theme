#! /bin/bash

export CKANINIPATH="/etc/ckan/default/ckan.ini"
export SITEURL='ckan.site_url = http'
export SITEURL_REPLACEMENT='ckan.site_url = https'
export SSLNAME='ckan_host'

# uwsgi script & server
echo $SUDOPASS | sudo -S -k cp /usr/lib/ckan/default/src/ckan/wsgi.py /etc/ckan/default/
. /usr/lib/ckan/default/bin/activate
pip3 install uwsgi
echo $SUDOPASS | sudo -S -k cp /usr/lib/ckan/default/src/ckan/ckan-uwsgi.ini /etc/ckan/default/

# configure supervisor
echo $SUDOPASS | sudo -S -k apt-get -y install supervisor=4.1.0-1ubuntu1
echo $SUDOPASS | sudo -S -k cp `pwd`/../config/supervisor/ckan-uwsgi.conf /etc/supervisor/conf.d/ckan-uwsgi.conf

# install an email server 

# install and configure nginx
echo $SUDOPASS | sudo -S -k apt-get -y install nginx=1.18.0-0ubuntu1.3
cp `pwd`/../config/nginx/localckan /etc/nginx/sites-available/
# Generate and configure a certificate
# Create SSL certificate
# https://docs.ckan.org/en/2.9/maintaining/configuration.html#ckan-devserver-ssl-cert
openssl genrsa 2048 > $SSLNAME.key
chmod 400 $SSLNAME.key
openssl req -new -x509 -nodes -sha256 -days 3650 -key $SSLNAME.key -subj "/C=CA/ST=ON/L=./O=ODS/OU=./CN=." > $SSLNAME.cert

# Modify ckan.ini to point ckan.site_url to localhost instead of localhost:5000
# Backup original config file
cd /etc/nginx/sites-available/
cp ckan ckan_orig
mv localckan ckan

# Modify site_url in ckan.ini
sed -i -r 's/'"$SITEURL"'/'"$SITEURL_REPLACEMENT"'/g' $CKANINIPATH

# Restart NGINX and supervisor
echo $SUDOPASS | sudo -S -k service nginx restart
echo $SUDOPASS | sudo -S -k supervisor restart
