#! /bin/bash

export $SUDOPASS='1'
# echo $SUDOPASS | sudo -S -k apt-get install -y git git-core

# Install Dependencies
echo "Installing packages..."
echo $SUDOPASS | sudo -S -k apt-get update
echo $SUDOPASS | sudo -S -k apt-get install -y libpq-dev redis-server python3-pip python3-virtualenv python3-dev python3.8-venv postgresql postgresql-contrib

