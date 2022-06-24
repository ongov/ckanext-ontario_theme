#! /bin/bash
source ./helper_functions.sh

#export SUDOPASS='mypass'

CKAN_ONT_THEME_ROOT="`pwd`/.."
CKAN_VENV='/usr/lib/ckan/default'
cd $CKAN_VENV/src/
. /usr/lib/ckan/default/bin/activate

# install ckan schema
pip3 install -e "git+https://github.com/ckan/ckanext-scheming.git#egg=ckanext-scheming"

# install fluent
git clone https://github.com/ckan/ckanext-fluent.git
cd ckanext-fluent
python3 setup.py develop
pip3 install -r requirements.txt

# install ontario theme
cd $CKAN_ONT_THEME_ROOT
python3 setup.py develop
pip3 install -r dev-requirements.txt
