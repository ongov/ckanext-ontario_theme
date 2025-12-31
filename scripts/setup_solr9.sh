#!/bin/bash

# Assume that the sudo password has been exported as an environment variable
# export SUDOPASS="mypassword"

# Vars
SOLRVER=9.10.0
STATUS_ERROR_MSG='Solr failed to install. Check status_out.txt.'

# Install Dependencies
echo "Installing packages..."
echo $SUDOPASS | sudo -S -k apt-get update
echo $SUDOPASS | sudo -S -k apt-get install -y openjdk-11-jdk

# Install and Configure SOLR
echo "Installing Solr binary installer for version ${SOLRVER}..."
wget --content-disposition --trust-server-names \
"https://www.apache.org/dyn/closer.lua/solr/solr/$SOLRVER/solr-$SOLRVER.tgz?action=download"
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
export CKANCONFDIR='/opt/solr/server/solr/configsets/ckan_conf/conf'
export CKANCONFROOT='/opt/solr/server/solr/configsets/ckan_conf'

echo $SUDOPASS | sudo -S -k /opt/solr/bin/solr stop -all
echo $SUDOPASS | sudo -S -k rm -rf /var/solr/data/ckan
echo $SUDOPASS | sudo -S -k mkdir -p $CKANCONFDIR
cd $CKANCONFDIR
echo $SUDOPASS | sudo -S -k chown -R `whoami` .
echo $SUDOPASS | sudo -S -k chmod -R u+rwx .
cp $REPODIR/../config/solr/managed-schema .
cp $REPODIR/../config/solr/solrconfig.xml .
cp $REPODIR/../config/solr/protwords.txt .
cp $REPODIR/../config/solr/stopwords.txt .
cp $REPODIR/../config/solr/synonyms.txt .
cp -r $REPODIR/../config/solr/lang .
echo $SUDOPASS | sudo -S -k chmod 775 *
echo "Schema fetched."

echo "Creating a CKAN core..."
echo $SUDOPASS | sudo -S -k -u solr /opt/solr/bin/solr restart -Dsolr.modules=analysis-extras
echo $SUDOPASS | sudo -S -k -u solr /opt/solr/bin/solr create -c ckan -d $CKANCONFROOT
echo "CKAN core created."
