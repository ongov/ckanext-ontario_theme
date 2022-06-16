#!/bin/bash

# Assume that the sudo password has been exported as an environment variable
# export SUDOPASS="mypassword"
# Assume that the Azure params have previously been exported
# AZUREBLOB, AZURECONTAINER, AZURESECRET
export STORAGEPY="/usr/lib/ckan/default/src/ckanext-cloudstorage/ckanext/cloudstorage/storage.py"
export MULTIPARTPY="/usr/lib/ckan/default/src/ckanext-cloudstorage/ckanext/cloudstorage/logic/action/multipart.py"
export PYLONSIMPORT="from pylons import config"
export PYLONSIMPORT_REPLACEMENT="from ckantoolkit import config"
export CKANINI="/etc/ckan/default/ckan.ini"
export CKANPLUGINS="recline_view datastore xloader"
export CKANPLUGINS_REPLACEMENT="recline_view datastore xloader cloudstorage"
export AZURESNIPPET="/usr/lib/ckan/default/src/ckanext-ontario_theme/config/cloudstorage/azure_snippet.txt"

. /usr/lib/ckan/default/bin/activate
pip3 install apache-libcloud==2.8.2

cd /usr/lib/ckan/default/src/
git clone https://github.com/DataShades/ckanext-cloudstorage.git
cd ckanext-cloudstorage
git fetch origin py3:py3
git checkout py3
python3 setup.py develop

pip3 install -r dev-requirements.txt
pip3 install zope.interface==5.0.0

# Make additional py3 upgrades
cd /usr/lib/ckan/default/src/ckanext-cloudstorage
git checkout -b ckan2.9
sed -i -r 's/'"$PYLONSIMPORT"'/'"$PYLONSIMPORT_REPLACEMENT"'/g' $STORAGEPY
sed -i -r 's/'"$PYLONSIMPORT"'/'"$PYLONSIMPORT_REPLACEMENT"'/g' $MULTIPARTPY

python3 setup.py develop
python3 setup.py install

# Add cloudstorage to ckan.plugins in ckan.ini
sed -i -r 's/'"$CKANPLUGINS"'/'"$CKANPLUGINS_REPLACEMENT"'/g' $CKANINI

# Add Azure params to snippet
sed -i '/<blob name>/ r '"$AZUREBLOB"'' $AZURESNIPPET
sed -i '/<storage container name>/ r '"$AZURECONTAINER"'' $AZURESNIPPET
sed -i '/<access key 1>/ r '"$AZURESECRET"'' $AZURESNIPPET

# Add cloudstorage params to ckan.ini
sed -i '/'"$CKANPLUGINS_REPLACEMENT"'/ r '"$AZURESNIPPET"'' $CKANINI

echo $SUDOPASS | sudo -S service supervisor restart

deactivate
