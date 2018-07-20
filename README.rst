.. You should enable this project on travis-ci.org and coveralls.io to make
   these badges work. The necessary Travis and Coverage config files have been
   generated for you.

.. image:: https://travis-ci.org/boykoc/ckanext-ontario_theme.svg?branch=master
    :target: https://travis-ci.org/boykoc/ckanext-ontario_theme

.. image:: https://coveralls.io/repos/boykoc/ckanext-ontario_theme/badge.svg
  :target: https://coveralls.io/r/boykoc/ckanext-ontario_theme

.. image:: https://pypip.in/download/ckanext-ontario_theme/badge.svg
    :target: https://pypi.python.org/pypi//ckanext-ontario_theme/
    :alt: Downloads

.. image:: https://pypip.in/version/ckanext-ontario_theme/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-ontario_theme/
    :alt: Latest Version

.. image:: https://pypip.in/py_versions/ckanext-ontario_theme/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-ontario_theme/
    :alt: Supported Python versions

.. image:: https://pypip.in/status/ckanext-ontario_theme/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-ontario_theme/
    :alt: Development Status

.. image:: https://pypip.in/license/ckanext-ontario_theme/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-ontario_theme/
    :alt: License

=============
ckanext-ontario_theme
=============

Theme for ontario ckan.


------------
Requirements
------------

For example, you might want to mention here which versions of CKAN this
extension works with.


------------
Installation
------------

To install ckanext-ontario_theme for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/boykoc/ckanext-ontario_theme.git
    cd ckanext-ontario_theme
    python setup.py develop
    pip install -r dev-requirements.txt


-----------------
Development
-----------------

Follow the `CKAN style rules <http://docs.ckan.org/en/latest/contributing/css.html#formatting>`_.

Converting to Less for styling.

This is the current process until a cleaner setup can be created.

Intall npm and less, then compile less files to css before pushing changes.

::
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

To run the tests, do::

    nosetests --nologcapture --with-pylons=test.ini

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run::

    nosetests --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.ontario_theme --cover-inclusive --cover-erase --cover-tests


---------------------------------
Registering ckanext-ontario_theme on PyPI
---------------------------------

ckanext-ontario_theme should be availabe on PyPI as
https://pypi.python.org/pypi/ckanext-ontario_theme. If that link doesn't work, then
you can register the project on PyPI for the first time by following these
steps:

1. Create a source distribution of the project::

     python setup.py sdist

2. Register the project::

     python setup.py register

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the first release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.1 then do::

       git tag 0.0.1
       git push --tags


----------------------------------------
Releasing a New Version of ckanext-ontario_theme
----------------------------------------

ckanext-ontario_theme is availabe on PyPI as https://pypi.python.org/pypi/ckanext-ontario_theme.
To publish a new version to PyPI follow these steps:

1. Update the version number in the ``setup.py`` file.
   See `PEP 440 <http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers>`_
   for how to choose version numbers.

2. Create a source distribution of the new version::

     python setup.py sdist

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the new release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.2 then do::

       git tag 0.0.2
       git push --tags
