=============
ckanext-ontario_theme
=============

Theme for Ontario ckan.


------------
Requirements
------------

CKAN 2.8.x
`ckanapi-exporter <https://github.com/ckan/ckanapi-exporter>`_


------------
Installation
------------

To install ckanext-ontario_theme for development, activate your CKAN 
virtualenv and do::

    git clone https://github.com/boykoc/ckanext-ontario_theme.git
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
    cd /ckanext-ontario_theme/ckanext/ontario_theme/fanstatic
    lessc ontario_theme.less ontario_theme.css

Styles should be broken down into small modules that do one thing and contain all necessary 
styling for that module. As an example, the smarties.less file should contain all styling
needed for smarties.

-----------------
Running the Tests
-----------------

To run the tests, make sure your ckan install is `setup for tests <https://docs.ckan.org/en/latest/contributing/test.html>`_, do::

    nosetests --nologcapture --with-pylons=test.ini

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run::

    nosetests --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.ontario_theme --cover-inclusive --cover-erase --cover-tests