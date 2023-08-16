#!/bin/bash

# Assume that the sudo password has been exported as an environment variable
# export SUDOPASS="mypassword"

# Vars
SOLRVER=8.11.2
STATUS_ERROR_MSG='Solr failed to install. Check status_out.txt.'

# Install Dependencies
echo "Installing packages..."
echo $SUDOPASS | sudo -S -k apt-get update
echo $SUDOPASS | sudo -S -k apt-get install -y net-tools=1.60+git20180626.aebd88e-1ubuntu1 openjdk-11-jre-headless

# Install and Configure SOLR
echo "Installing Solr binary installer for version ${SOLRVER}..."
wget https://dlcdn.apache.org/lucene/solr/$SOLRVER/solr-$SOLRVER.tgz
tar xzf solr-$SOLRVER.tgz
sleep 5
echo $SUDOPASS | sudo -S -k ./solr-$SOLRVER/bin/install_solr_service.sh solr-$SOLRVER.tgz > status_out.txt
sleep 5
STATUSCHECK=$(grep 'status=0/SUCCESS' status_out.txt | wc -l)
if [[ $STATUSCHECK -eq 0 ]]; then
     echo >&2 "ERROR: $STATUS_ERROR_MSG"; exit 1;
fi
echo "Solr is running."
echo $SUDOPASS | sudo -S -k chown -R `whoami` /opt/solr/server/

echo "Fetching managed-schema for ontario_theme..."
export REPODIR=`pwd`
cd /opt/solr/server/solr/configsets/_default/
echo $SUDOPASS | sudo -S -k chown -R `whoami` .
echo $SUDOPASS | sudo -S -k chmod -R u+rwx .
# Make a backup copy of managed-schema
cd conf/
mv managed-schema managed-schema.bk
cp $REPODIR/../config/solr/managed-schema .
echo $SUDOPASS | sudo -S -k chmod 775 managed-schema
echo "Schema fetched."

# New CKAN core creation method
echo "Creating a CKAN core..."
echo $SUDOPASS | sudo -S -k /opt/solr/bin/solr stop -all
sudo rm -rf /var/solr/data/ckan
sudo mkdir -p /opt/solr/server/solr/configsets/ckan_conf/conf
sudo cp /usr/lib/ckan/default/src/ckanext-ontario_theme/config/solr/managed-schema /opt/solr/server/solr/configsets/ckan_conf/conf
sudo cp /lib/ckan/default/src/ckanext-ontario_theme/config/solr/solrconfig.xml /opt/solr/server/solr/configsets/ckan_conf/conf
sudo cp /lib/ckan/default/src/ckanext-ontario_theme/config/solr/protwords.txt /opt/solr/server/solr/configsets/ckan_conf/conf
sudo cp /lib/ckan/default/src/ckanext-ontario_theme/config/solr/stopwords.txt /opt/solr/server/solr/configsets/ckan_conf/conf
sudo cp /lib/ckan/default/src/ckanext-ontario_theme/config/solr/synonyms.txt /opt/solr/server/solr/configsets/ckan_conf/conf
sudo -u solr /opt/solr/bin/solr restart
sudo -u solr /opt/solr/bin/solr create -c ckan -d /opt/solr/server/solr/configsets/ckan_conf/conf
echo "CKAN core created."



