#! /bin/bash
source ./helper_functions.sh

export CKANINIROOT="/etc/ckan/default/"
export CKANINIPATH=$CKANINIROOT"ckan.ini"

# uwsgi script & server
echo $SUDOPASS | sudo -S -k cp /usr/lib/ckan/default/src/ckan/wsgi.py /etc/ckan/default/
echo $SUDOPASS | sudo -S -k chown www-data /etc/ckan/default/wsgi.py
. /usr/lib/ckan/default/bin/activate
pip3 install -Iv uwsgi==2.0.20
echo $SUDOPASS | sudo -S -k cp /usr/lib/ckan/default/src/ckan/ckan-uwsgi.ini /etc/ckan/default/

# configure supervisor
echo $SUDOPASS | sudo -S -k apt-get -y install supervisor=4.1.0-1ubuntu1
echo $SUDOPASS | sudo -S -k cp `pwd`/../config/supervisor/ckan-uwsgi.conf /etc/supervisor/conf.d/ckan-uwsgi.conf

# install an email server 
# TODO

# install and configure nginx
echo $SUDOPASS | sudo -S -k apt-get -y install nginx=1.18.0-0ubuntu1.3
echo $SUDOPASS | sudo -S -k cp `pwd`/../config/nginx/local_ckan_ssl /etc/nginx/sites-available/
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
