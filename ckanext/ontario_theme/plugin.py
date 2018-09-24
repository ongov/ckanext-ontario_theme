import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class OntarioThemePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'ontario_theme')
        # Uncomment these to use bootstrap 2 theme and comment out
        # the above template and resource directories.
        # toolkit.add_template_directory(config_, 'templates-bs2')
        # toolkit.add_resource('fanstatic-bs2', 'ontario_theme')
