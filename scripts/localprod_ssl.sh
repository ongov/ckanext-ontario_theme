#! /bin/bash

# Script to install mkcert to create SSL certificates
# https://github.com/FiloSottile/mkcert
#
# Requires Go

# --------------------------------------------------------
# Variables for CKAN
export CKANINIPATH="/etc/ckan/default/ckan.ini"
export SITEURL='ckan.site_url = http'
export SITEURL_REPLACEMENT='ckan.site_url = https'
export SSLNAME='ckan_host'

# --------------------------------------------------------
# Variables for Go
# Determine latest stable version to use for Linux [64-bit]
# from https://go.dev/dl/
export STABLE_VERSION='18.3'
export TAR_FILE=$(sed '' <<<"go1.$STABLE_VERSION.linux-amd64.tar.gz")
# Store the checksum associated with $STABLE_VERSION
export CHECKSUM='956f8507b302ab0bb747613695cdae10af99bbd39a90cae522b7c0302cc27245'
# Construct the wget command to download $STABLE_VERSION
export WGET_STRING=$(sed '' <<<"https://golang.org/dl/$TAR_FILE")

# --------------------------------------------------------
# Variables for mkcert
export CERT_NAME='ckan_cert'

# --------------------------------------------------------
# Install Go (follows https://www.tecmint.com/install-go-in-linux/)
# Download latest stable version
wget -c $WGET_STRING

# Check the integrity of the tar ball by verifying that 
# the shasum returned matches $CHECKSUM
GO_INSTALLED_CHECKSUM="`shasum -a 256 $(sed '' <<<"$TAR_FILE")`"
VALID_CHECKSUM="$CHECKSUM $(sed '' <<<" $TAR_FILE")"

if [[ $GO_INSTALLED_CHECKSUM == $VALID_CHECKSUM ]]; then
  echo "Tarball integrity check passed."
else
  echo "Incorrect checksum on Go tarball."; exit 1;
fi

echo $SUDOPASS | sudo -S tar -C /usr/local -xvzf $TAR_FILE
rm $TAR_FILE

# Add Go to path
export PATH=$PATH:/usr/local/go/bin

# --------------------------------------------------------
# Install certutil
echo $SUDOPASS | sudo -S apt install libnss3-tools

# --------------------------------------------------------
# Install mkcert 
git clone https://github.com/FiloSottile/mkcert && cd mkcert
go build -ldflags "-X main.Version=$(git describe --tags)"

cd mkcert
./mkcert -install
# The local CA is now installed in the system trust store! ⚡️
# The local CA is now installed in the Firefox and/or Chrome/Chromium trust store (requires browser restart)! 🦊
firefox &

# Move certificates to same directory as ckan.ini
mv $(sed '' <<<"$CERT_NAME.com*.pem") /etc/ckan/default/

# --------------------------------------------------------
# Set up NGINX config file

# Retrieve template config file
cp /usr/lib/ckan/default/src/ckanext-ontario_theme/config/nginx/localckan /etc/nginx/sites-available/

# Backup original config file
cd /etc/nginx/sites-available/
cp ckan ckan_orig
mv localckan ckan

# Modify site_url in ckan.ini
sed -i -r 's/'"$SITEURL"'/'"$SITEURL_REPLACEMENT"'/g' $CKANINIPATH

# Restart NGINX and supervisor
echo $SUDOPASS | sudo -S service nginx restart
sudo service supervisor restart
