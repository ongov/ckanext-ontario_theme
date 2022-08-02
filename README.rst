=============
ckanext-ontario_theme
=============

Theme for Ontario ckan including:

* metadata schema
* forms
* templates and design


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
   - ckan-2.9.x
   - N/A
 * - Scheming extension
   - `open-data/ckanext-scheming <https://github.com/open-data/ckanext-scheming>`_
   - master
   - ``scheming_datasets``
 * - Fluent extension
   - `open-data/ckanext-fluent <https://github.com/open-data/ckanext-fluent>`_
   - master
   - ``fluent``
 * - Harvest extension
   - `ckan/ckanext-harvest <https://github.com/ckan/ckanext-harvest>`_
   - master
   - ``harvest``

(The harvest extension might not run without adding the following command "sudo mkdir -p /var/log/ckan/std")

------------
Plugins in this Extension
------------

* ``ontario_theme`` base and internal facing Ontario data catalogue
* ``ontario_theme_external`` customizations for external facing Ontario data catalogue (requires ``ontario_theme``)
* ``ontario_data_catalogue_harvester`` harvester for internal data catalogue to sync with the external data catalogue.


------------
Installation
------------

To install ckanext-ontario_theme for development, activate your CKAN 
virtualenv and do::

    git clone https://github.com/ongov/ckanext-ontario_theme.git
    cd ckanext-ontario_theme
    python setup.py develop
    pip install -r dev-requirements.txt
    
    python setup.py develop
    pip install -r dev-requirements.txt

Update the development.ini (or production.ini) plugins::

    # This relies on scheming and fluent, make sure these are already installed.
    # Note: This extension needs to be before scheming and fluent in the *.ini config file to let the form overrides work.
    
    # For external catalogue
    ckan.plugins = [...] ontario_theme_external ontario_theme scheming_datasets scheming_organizations scheming_groups fluent [...]

    # For internal catalogue
    ckan.plugins = [...] ontario_data_catalogue_harvester ontario_theme harvest scheming_datasets scheming_organizations scheming_groups fluent [...]

    # For both, add licenses:
    licenses_group_url = file:///<path to this extension>/ckanext/ontario_theme/schemas/licences.json

Setup for CKAN tracking (https://docs.ckan.org/en/2.9/maintaining/tracking.html). The config setting is in the `plugin.py` already.

Create a sysadmin user, login and set the HomePage layout under Admin -> Config to the third option. Our homepage uses this layout as it's base.

------------
Harvesters
------------

ontario_data_catalogue_harvester - only for use on the internal catalogue. add the plugin in the ini file and restart the server. visit /harvest and add a harvester for the url https://data.ontario.ca

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
    pytest --ckan-ini=test.ini ckanext/ontario_theme/tests/

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run::

    coverage run -m pytest --ckan-ini=test.ini ckanext/ontario_theme/tests/

You can then run:: 

    coverage html

or::

    coverage report

You can then find the coverage reports in a generated htmlcov folder.

Our custom config settings are in ``./test.ini``.

Additional ways to run tests:

    # Single Test class
    coverage run -m pytest --ckan-ini=test.ini ckanext/ontario_theme/tests/test_create_dataset.py::test_package_create_with_invalid_update_frequency 

    # Single Test module
    coverage run -m pytest --ckan-ini=test.ini ckanext/ontario_theme/tests/test_create_dataset.py
