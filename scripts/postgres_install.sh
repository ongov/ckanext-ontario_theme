#! /bin/bash

export SUDOPASS='1'
export CKANUSER='ckan_default'
export CKANPASS='ckan_default'
export CKANDB='ckan_default'
export DATASTOREUSER='datastore_default'
export DATASTOREPASS='datastore_default'
export DATASTOREDB='datastore_default'

# Install Postgres Dependencies
echo "Installing packages..."
echo $SUDOPASS | sudo -S -k apt-get update
echo $SUDOPASS | sudo -S -k apt-get install -y libpq-dev postgresql postgresql-contrib

# PostgreSQL db setup
output=`echo $SUDOPASS | sudo -S -k -u postgres psql -l`

# CKAN DB
echo $SUDOPASS | sudo -S -k -u postgres psql -c "CREATE USER \"$CKANUSER\" WITH PASSWORD '$CKANPASS' NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN"
echo $SUDOPASS | sudo -S -k -u postgres psql -c "CREATE DATABASE $CKANDB OWNER \"$CKANUSER\" ENCODING UTF8"

# DATASTORE DB
echo $SUDOPASS | sudo -S -k -u postgres psql -c "CREATE USER \"$DATASTOREUSER\" WITH PASSWORD '$DATASTOREPASS' NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN"
echo $SUDOPASS | sudo -S -k -u postgres psql -c "CREATE DATABASE $DATASTOREDB OWNER \"$CKANUSER\" ENCODING UTF8"

