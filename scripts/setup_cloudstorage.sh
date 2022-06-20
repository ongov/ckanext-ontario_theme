#!/bin/bash
source ./helper_functions.sh

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
replace_str_in_file "$PYLONSIMPORT" "$PYLONSIMPORT_REPLACEMENT" "$STORAGEPY"
replace_str_in_file "$PYLONSIMPORT" "$PYLONSIMPORT_REPLACEMENT" "$MULTIPARTPY"

python3 setup.py develop
python3 setup.py install

# Add cloudstorage to ckan.plugins in ckan.ini
replace_str_in_file "$CKANPLUGINS" "$CKANPLUGINS_REPLACEMENT" "$CKANINI"

# Add Azure snippet to ckan.ini
sed -i '/'"$CKANPLUGINS_REPLACEMENT"'/ r '"$AZURESNIPPET"'' $CKANINI

# Replace Azure placeholders with pre-defined values
replace_str_in_file "<blob name>" "$AZUREBLOB" "$CKANINI"
replace_str_in_file "<storage container name>" "$AZURECONTAINER" "$CKANINI"
# Escape special characters in Azure secret with str_to_sed_str() 
# and duplicate any % chars
AZURESECRET_FORMATTED=$(str_to_sed_str $(sed '/%/s/$/%%/' <<<$AZURESECRET))
# Store formatted Azure secret in a text file
echo "\"${AZURESECRET_FORMATTED}\"" > secret_snippet.txt
# Add secret to ckan.ini by appending text file
sed -i '/"secret":/ r secret_snippet.txt' $CKANINI
rm secret_snippet.txt

echo $SUDOPASS | sudo -S service supervisor restart

deactivate
