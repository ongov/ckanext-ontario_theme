=============
ckanext-extrafields
=============

Adds additional metadata fields to CKAN.


------------
Requirements
------------

Works with CKAN version 2.7.


------------------------
Installation
------------------------

To install ckanext-extrafields for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/boykoc/ckanext-extrafields.git
    cd ckanext-extrafields
    python setup.py develop
    pip install -r dev-requirements.txt

Add the extension to development.ini or production.ini and set the dataset schema::

    # This relies on scheming and fluent, make sure these are already installed.
    ckan.plugins = extrafields
    # Specify the new schema for datasets.
    scheming.dataset_schemas = ckanext.extrafields:ontario_theme_dataset.json
    scheming.presets = ckanext.scheming:presets.json
                       ckanext.fluent:presets.json


-----------------
Running the Tests
-----------------

To run the tests, do::

    cd ckanext-extrafields # go to extension directory
    . /usr/lib/ckan/default/bin/activate # active vertual environment that has nosetests.
    nosetests --nologcapture --with-pylons=test.ini # run tests

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run::

    nosetests --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.extrafields --cover-inclusive --cover-erase --cover-tests
