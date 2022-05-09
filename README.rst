=============
ckanext-ontario_theme
=============

Theme for Ontario ckan including:

* metadata schema
* forms
* templates and design

-------------------
Directory Structure
-------------------
Four directories compose this repository

* **scripts:** contains scripts to setup CKAN and required applications
* **config:** contains configuration files needed for installation and configuration of CKAN
* **ckanext:** Ontario Theme Extension files for CKAN
* **bin:** contains CI scripts that are no longer being used. This directory is pending deletion/cleanup

------------
Requirements
------------

.. list-table:: Related projects, repositories, branches and CKAN plugins
 :header-rows: 1

 * - Project
   - Github group/repo
   - Branch
   - Plugins
 * - CKAN
   - `ckan/ckan <https://github.com/ckan/ckan/>`_
   - ckan-2.8.x
   - N/A
 * - Scheming extension
   - `open-data/ckanext-scheming <https://github.com/open-data/ckanext-scheming>`_
   - master
   - ``scheming_datasets``
 * - Fluent extension
   - `open-data/ckanext-fluent <https://github.com/open-data/ckanext-fluent>`_
   - master
   - ``fluent``
 * - ckanapi-exporter
   - `ckanapi-exporter <https://github.com/ckan/ckanapi-exporter>`_
   - master
   - N/A


------------
Plugins in this Extension
------------

* ``ontario_theme`` base and internal facing Ontario data catalogue
* ``ontario_theme_external`` customizations for external facing Ontario data catalogue (requires ``ontario_theme``)


------------
Installation
------------

To install ckanext-ontario_theme for development, activate your CKAN 
virtualenv and do::

    git clone https://github.com/ongov/ckanext-ontario_theme.git
    cd ckanext-ontario_theme
    python setup.py develop
    pip install -r dev-requirements.txt
    
    # Install ckanapi-exporter master from github to get around query limit 
    # of 1000 datasets in package_search.
    # TODO: Update to pip install after new release.
    git clone https://github.com/ckan/ckanapi-exporter.git
    cd ckanapi-exporter
    python setup.py develop
    pip install -r dev-requirements.txt

Update the development.ini (or production.ini) plugins::

    # This relies on scheming and fluent, make sure these are already installed.
    # Note: This extension needs to be before scheming and fluent in the *.ini config file to let the form overrides work.
    
    # For external catalogue
    ckan.plugins = [...] ontario_theme_external ontario_theme scheming_datasets scheming_organizations scheming_groups fluent [...]

    # For internal catalogue
    ckan.plugins = [...] ontario_theme scheming_datasets scheming_organizations scheming_groups fluent [...]

    # For both, add licenses:
    licenses_group_url = file:///<path to this extension>/ckanext/ontario_theme/schemas/licences.json

Setup for CKAN tracking by running the paster cmds and adding cron jobs. The
config setting is in the `plugin.py` already::

    paster --plugin=ckan tracking update --config=/etc/ckan/default/production.ini
    paster --plugin=ckan search-index rebuild --config=/etc/ckan/default/production.ini
    crontab -e
    # Add this line
    @hourly /usr/lib/ckan/default/bin/paster --plugin=ckan tracking
    update -c /etc/ckan/default/production.ini && /usr/lib/ckan/default/bin/paster --plugin=ckan search-index rebuild -r -c /etc/ckan/default/production.ini

Create a sysadmin user, login and set the HomePage layout under Admin -> Config to the third option. Our homepage uses this layout as it's base.

-----------------
Development
-----------------

Follow the `CKAN style rules <http://docs.ckan.org/en/latest/contributing/css.html#formatting>`_.

Converting to Less for styling.

This is the current process until a cleaner setup can be created.

Install npm and less, then compile less files to css before pushing changes.::

    sudo apt install npm
    sudo npm install -g less
    ln -s /usr/bin/nodejs /usr/bin/node
    cd /ckanext-ontario_theme/ckanext/ontario_theme/fanstatic/internal
    lessc ontario_theme.less ontario_theme.css # Builds internal
    cd ../external
    lessc ontario_theme.less ontario_theme.css # Builds external

Styles should be broken down into small modules that do one thing and contain all necessary 
styling for that module. As an example, the smarties.less file should contain all styling
needed for smarties.


-----------------
Translations
-----------------

Current Process:

* We currently do them manually
* We have not been updating the line numbers or comments at all
* We edit the .pot and .po files manually for new and modified strings
* the .mo file is generated at deployment on the server with ``python setup.py compile_catalog`` from the ``ckanext-ontario_theme`` directory

Initial Creation:

* Initially the .pot file was created as per docs (``python setup.py extract_messages``) and we generated the .po file for our locale as well (``python setup.py init_catalog -l fr``). Some tweaks were made for formatting large strings and removing things that are covered by the CKAN .po files (e.g. "Dataset" is already translated).

Additional Info:

* you have a template file (.pot) that has the ``msgid`` and the empty ``msgstr``.
* the template can be used to create other locale translation files (e.g. French, Spanish, German, etc.)
* the translation files (.po) have the "id" and the translation for that locale. The translation text is manually added in (or with something like Transifex).
* the .mo file is the compiled translation for each locale that is used when displaying the site in that locale.
* Note: if you regenerate the .pot file it replaces the existing one based on the current state of the templates. If you then regenerate the .po file it does the same and all translation content will be lost unless you do an update and go through for edits. It's partially why this form of translations are for things that are static content that change rarely. More dynamic content should be handled elsewhere (e.g. see ckanext-fluent)


-----------------
Running the Tests
-----------------

To run the tests, make sure your ckan install is `setup for tests <https://docs.ckan.org/en/latest/contributing/test.html>`_, do::

    cd ckanext-ontario_theme # go to extension directory
    nosetests --nologcapture --with-pylons=test.ini # run in virtual environment that has nosetests.

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run::

    nosetests --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.ontario_theme --cover-inclusive --cover-erase --cover-tests

Our custom config settings are in ``./test.ini``.

Additional ways to run tests:

    # Single Test method
    nosetests ckanext/ontario_theme/tests/test_create_dataset.py:TestCreateDataset.test_package_create_with_invalid_update_frequency --nologcapture --with-pylons=test.ini
    # Single Test class
    nosetests ckanext/ontario_theme/tests/test_create_dataset.py:TestCreateDataset --nologcapture --with-pylons=test.ini
    # Single Test module
    nosetests ckanext/ontario_theme/tests/test_create_dataset.py --nologcapture --with-pylons=test.ini