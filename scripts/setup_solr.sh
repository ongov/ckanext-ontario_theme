#!/bin/bash

# Assume that the sudo password has been exported as an environment variable
# export SUDOPASS="mypassword"

# Vars
SOLRVER=8.11.1
STATUS_ERROR_MSG='Solr failed to install. Check status_out.txt.'

# Install Dependencies
echo "Installing packages..."
echo $SUDOPASS | sudo -S -k apt-get update
echo $SUDOPASS | sudo -S -k apt-get install -y net-tools=1.60+git20180626.aebd88e-1ubuntu1 openjdk-11-jre=11.0.15+10-0ubuntu0.20.04.1

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

echo "Creating a ckan core..."
echo $SUDOPASS | sudo -S -k -u solr /opt/solr/bin/solr create -c ckan
echo "ckan core created."

