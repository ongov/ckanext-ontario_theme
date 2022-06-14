#! /bin/bash

export SUDOPASS='1'
export CKANUSER='ckan_default'
export CKANPASS='ckan_default'
export CKANDB='ckan_default'
export DATASTOREUSER='datastore_default'
export DATASTOREPASS='datastore_default'
export DATASTOREDB='datastore_default'

# echo $SUDOPASS | sudo -S -k apt-get install -y git git-core

# Install Dependencies
echo "Installing packages..."
echo $SUDOPASS | sudo -S -k apt-get update
echo $SUDOPASS | sudo -S -k apt-get install -y libpq-dev redis-server python3-pip python3-virtualenv python3-dev python3.8-venv

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

# TODO: Configuring ckan.ini to /etc/ckan/default/


# Link to who.ini
ln -s /usr/lib/ckan/default/src/ckan/who.ini /etc/ckan/default/who.ini

# setup filestore & ckan admin account
ckan -c /etc/ckan/default/ckan.ini sysadmin add admin email=admin@localhost name=admin
echo $SUDOPASS | sudo chown -R `whoami` /usr/lib/ckan/default
echo $SUDOPASS | sudo chown -R u+rw /usr/lib/ckan/default

# setup datastore


# xloader


