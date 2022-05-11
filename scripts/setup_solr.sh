#!/bin/bash

# Assume that the sudo password has been exported as an environment variable
# export SUDOPASS="mypassword"

# Vars
SOLRVER=8.11.1

# Install Dependencies
echo "Installing packages..."
echo $SUDOPASS | sudo -S -k apt-get update
echo $SUDOPASS | sudo -S -k apt-get install -y net-tools openssh-server openjdk-11-jre

# Install and Configure SOLR
echo "Installing Solr binary installer for version ${SOLRVER}..."
wget https://dlcdn.apache.org/lucene/solr/$SOLRVER/solr-$SOLRVER.tgz
tar xzf solr-$SOLRVER.tgz
sleep 5
echo $SUDOPASS | sudo -S -k ./solr-$SOLRVER/bin/install_solr_service.sh solr-$SOLRVER.tgz > status_out.txt
sleep 5
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

echo "Creating a CKAN core..."
echo $SUDOPASS | sudo -S -k su solr <<EOF
cd /opt/solr/bin
pwd
./solr create -c ckan
exit
EOF
echo "CKAN core created."

