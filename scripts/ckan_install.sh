#! /bin/bash

export SUDOPASS='1'
# echo $SUDOPASS | sudo -S -k apt-get install -y git git-core

# Install Dependencies
echo "Installing packages..."
echo $SUDOPASS | sudo -S -k apt-get update
echo $SUDOPASS | sudo -S -k apt-get install -y libpq-dev redis-server python3-pip python3-virtualenv python3-dev python3.8-venv postgresql postgresql-contrib

# Install CKAN into py virt env
echo $SUDOPASS | sudo -S -k mkdir -p /usr/lib/ckan/default
echo $SUDOPASS | sudo -S -k chown `whoami` /usr/lib/ckan/default
python3 -m venv /usr/lib/ckan/default
. /usr/lib/ckan/default/bin/activate

# install tools and ckan
pip3 install setuptools==45 wheel==0.37.1
pip3 install -e 'git+https://github.com/ckan/ckan.git@ckan-2.9.5#egg=ckan[requirements]'

# PostgreSQL db setup


