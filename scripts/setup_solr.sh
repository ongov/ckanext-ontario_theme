#!/bin/bash

# Assume that the sudo password has been exported as an environment variable
# export SUDOPASS="mysudopass"

echo "Installing packages..."
echo $SUDOPASS | sudo -S apt-get update
echo $SUDOPASS | sudo -S  apt-get install -y net-tools openssh-server openjdk-11-jre python3-pip python3-virtualenv python3-dev python3.8-venv git

SOLRVER=8.11.1
echo ""
echo "Installing Solr binary installer for version ${SOLRVER}..."
wget https://dlcdn.apache.org/lucene/solr/$SOLRVER/solr-$SOLRVER.tgz
tar xzf solr-$SOLRVER.tgz
echo $SUDOPASS | sudo -S ./solr-$SOLRVER/bin/install_solr_service.sh solr-$SOLRVER.tgz > status_out.txt
sleep 5
echo "Solr is running."
echo $SUDOPASS | sudo -S chown -R `whoami` /opt/solr/server/
ls -lt

echo "Fetching managed-schema for ontario_theme..."
git clone https://github.com/ongov/ckanext-ontario_theme.git
cd ckanext-ontario_theme
git fetch origin solr8:solr8
git checkout solr8
cd /opt/solr/server/solr/configsets/_default/
echo $SUDOPASS | sudo -S chown -R `whoami` .
echo $SUDOPASS | sudo -S chmod -R u+rwx .
# Make a backup copy of managed-schema
cd conf/
pwd
mv managed-schema managed-schema.bk
ls -lt
# Copy ontario_theme schema from repository
cp ~/ckanext-ontario_theme/config/solr/managed-schema .
sudo chmod 775 managed-schema
ls -lt
echo "Schema fetched."


echo ""
echo "Creating a CKAN core..."
sudo su solr <<EOF
cd /opt/solr/bin
pwd
./solr create -c ckan
exit
EOF
echo "CKAN core created."
