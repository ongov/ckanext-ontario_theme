import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from flask import Blueprint
from flask import render_template, render_template_string

def help():
    '''New help page for site.
    '''
    return render_template('home/help.html')

class OntarioThemePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'ontario_theme')
        # Uncomment these to use bootstrap 2 theme and comment out
        # the above template and resource directories.
        # toolkit.add_template_directory(config_, 'templates-bs2')
        # toolkit.add_resource('fanstatic-bs2', 'ontario_theme')

    # IBlueprint

    def get_blueprint(self):
        '''Return a Flask Blueprint object to be registered by the app.
        '''

        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'
        # Add url rules to Blueprint object.
        rules = [
            (u'/help', u'help', help)
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule)

        return blueprint
