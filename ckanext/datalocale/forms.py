import os
import pylons
import logging
import ckan.authz as authz
import ckan.logic as logic
from ckan.logic.converters import convert_to_extras,\
    convert_from_extras, convert_to_tags, convert_from_tags, free_tags_only
from ckan.logic import get_action, NotFound
from ckan.logic import NotAuthorized
from ckan.lib import base
from ckan.lib.base import c, model, abort, request
from ckan.plugins import IDatasetForm, IGroupForm, IConfigurer, IGenshiStreamFilter, IActions
from ckan.plugins import implements, SingletonPlugin
from ckan.logic import check_access
from ckan.lib.navl.validators import ignore_missing, keep_extras, not_empty
import ckan.lib.plugins
import ckan.plugins
from validators import datalocale_convert_from_tags, datalocale_convert_to_tags

log = logging.getLogger(__name__)

VOCAB_FREQUENCES = u'dct:accrualPeriodicity'
VOCAB_THEMES = u'dcat:themeTaxonomy'
VOCAB_THEMES_CONCEPT = u'dcat:theme'

def my_vocabulary_show(context, data_dict):
    context['for_view'] = True
    return logic.action.get.vocabulary_show(context, data_dict)

def _tags_and_translations(context, vocab, lang, lang_fallback):
    try:
	tags = logic.get_action('tag_list')(context, {'vocabulary_id': vocab})
	tag_translations = _translate(tags, lang, lang_fallback)
	return [(t, tag_translations[t]) for t in tags]
    except logic.NotFound:
	return []

def _translate(terms, lang, fallback_lang):
    translations = logic.get_action('term_translation_show')(
	{'model': model},
	{'terms': terms, 'lang_codes': [lang]}
    )

    term_translations = {}
    for translation in translations:
	term_translations[translation['term']] = translation['term_translation']

    for term in terms:
	if not term in term_translations:
	    translation = logic.get_action('term_translation_show')(
	        {'model': model},
	        {'terms': [term], 'lang_codes': [fallback_lang]}
	    )
	    if translation:
	        term_translations[term] = translation[0]['term_translation']
	    else:
	        term_translations[term] = term

    return term_translations

class DatalocaleDatasetForm(SingletonPlugin):
    """
      - ``IConfigurer`` allows us to override configuration normally
        found in the ``ini``-file.  Here we use it to specify where the
        form templates can be found.
      - ``IDatasetForm`` allows us to provide a custom form for a dataset
        based on the type_name that may be set for a package.  Where the
        type_name matches one of the values in package_types then this
        class will be used.
      - ``IGenshiStreamFilter`` hook into Pylons template rendering. 
      - ``IActions`` Allow adding of actions to the logic layer (API).

    """
    implements(IDatasetForm, inherit=True)
    implements(IConfigurer, inherit=True)
    implements(IGenshiStreamFilter, inherit=True)
    implements(IActions, inherit=True)

    def update_config(self, config):
        """
        This IConfigurer implementation causes CKAN to look in the
        ```templates``` directory when looking for the package_form()
        """
        here = os.path.dirname(__file__)
        rootdir = os.path.dirname(os.path.dirname(here))
        template_dir = os.path.join(rootdir, 'ckanext',
                                    'datalocale', 'theme', 'templates')
        config['extra_template_paths'] = ','.join([template_dir,
                config.get('extra_template_paths', '')])

    def package_form(self):
        return 'forms/dataset_form.html'

    def new_template(self):
        return 'package/new.html'

    def comments_template(self):
        return 'package/comments.html'

    def search_template(self):
        return 'package/search.html'

    def read_template(self):
        return 'forms/read.html'

    def history_template(self):
        return 'package/history.html'

    def is_fallback(self):
        return True

    def package_types(self):
        return ["dataset"]

    def setup_template_variables(self, context, data_dict, package_type=None):
        from pylons import config
	''' Translation '''
        ckan_lang = pylons.request.environ['CKAN_LANG']
        ckan_lang_fallback = pylons.config.get('ckan.locale_default', 'fr')

        data_dict.update({'available_only':True})
        c.groups_available = c.userobj and c.userobj.get_groups('organization') or []
        c.licences = [('', '')] + base.model.Package.get_license_options()
        c.is_sysadmin = authz.Authorizer().is_sysadmin(c.user)
	c.publishers_available = c.groups_available
	c.contributor = c.userobj
        try:
		data = {'vocabulary_id': VOCAB_FREQUENCES}
	       	c.frequences_available = get_action('tag_list')(context, data)
	except NotFound:
		c.frequences_available = []
    	try:
		data = {'vocabulary_id': VOCAB_THEMES}
		c.themeTaxonomy_available = _tags_and_translations(
		    context, 'dcat:themeTaxonomy', ckan_lang, ckan_lang_fallback
		)
	except NotFound:
		c.themeTaxonomy_available = []

    	
        ''' Find extras that are not part of our schema '''
        c.additional_extras = []
        schema_keys = self.form_to_db_schema().keys()
        if c.pkg_json:
            extras = json.loads(c.pkg_json).get('extras', [])
            for extra in extras:
                if not extra['key'] in schema_keys:
                    c.additional_extras.append(extra)
       
	'''This is messy as auths take domain object not data_dict'''
	context_pkg = context.get('package', None)
        pkg = context_pkg or c.pkg
        if pkg:
            try:
                if not context_pkg:
                    context['package'] = pkg
                check_access('package_change_state', context)
                c.auth_for_change_state = True
            except NotAuthorized:
                c.auth_for_change_state = False
	

    def form_to_db_schema(self, package_type=None):
        """
        Returns the schema for mapping package data from a form to a format
        suitable for the database.
        """
	from ckan.logic.schema import package_form_schema, default_package_schema
	from ckan.lib.navl.validators import ignore_missing
	from ckan.logic.converters import convert_to_tags, convert_to_extras
	
    	schema = package_form_schema()
    	schema.update({
        	'frequences_available': [ignore_missing, convert_to_tags(VOCAB_FREQUENCES)],
		'themeTaxonomy_available': [ignore_missing, convert_to_tags(VOCAB_THEMES)],
		'theme_available': [ignore_missing, datalocale_convert_to_tags('themeTaxonomy_available')],
		'dct:creator': [unicode, convert_to_extras, ignore_missing],
		'dct:publisher': [unicode, convert_to_extras, ignore_missing],
		'dct:contributor': [unicode, convert_to_extras, ignore_missing],
		'dct:temporal': [unicode, convert_to_extras, ignore_missing],
		'maj': [unicode, convert_to_extras, ignore_missing],
    	})
        schema['groups'].update({
            'capacity': [ignore_missing, unicode]
        })
        return schema

    def db_to_form_schema(self):
        """
        Returns the schema for mapping package data from the database into a
        format suitable for the form (optional)
        """
	from ckan.logic.converters import convert_from_tags, convert_from_extras, free_tags_only
    	from ckan.lib.navl.validators import ignore_missing, keep_extras
	from ckan.logic.schema import package_form_schema, default_package_schema, default_resource_schema
	schema = package_form_schema()
 	schema['resources'].update({
            'created': [ignore_missing],
            'position': [not_empty],
            'last_modified': [ignore_missing],
            'cache_last_updated': [ignore_missing],
            'webstore_last_updated': [ignore_missing]
        })
        schema['groups'].update({
	    'id': [ignore_missing],
            'name': [ignore_missing, unicode],
            'title': [ignore_missing],
            'capacity': [ignore_missing, unicode]
        })
    	schema.update({
		'tags': {
	    		'__extras': [keep_extras, free_tags_only]
		},
		'frequences_available': [convert_from_tags(VOCAB_FREQUENCES), ignore_missing],
		'themeTaxonomy_available': [convert_from_tags(VOCAB_THEMES), ignore_missing],
		'theme_available': [datalocale_convert_from_tags('themeTaxonomy_available'), ignore_missing],
		'dct:creator': [convert_from_extras, ignore_missing],
		'dct:publisher': [convert_from_extras, ignore_missing],
		'dct:contributor': [convert_from_extras, ignore_missing],
		'dct:temporal': [convert_from_extras, ignore_missing],
		'maj': [convert_from_extras, ignore_missing],
		'isopen' : [ignore_missing],
		'resources': [ignore_missing],
    	})
        return schema

    def check_data_dict(self, data_dict, schema=None):
        '''Check if the return data is correct, mostly for checking out
	if spammers are submitting only part of the form'''

        # Resources might not exist yet (eg. Add Dataset)
        surplus_keys_schema = ['__extras', '__junk', 'state', 'groups',
                               'extras_validation', 'save', 'return_to',
                               'resources', 'type']

    def filter(self, stream):
        ''' Add vocab tags to the bottom of the sidebar.'''
        from pylons import request
        from genshi.filters import Transformer
        from genshi.input import HTML
        routes = request.environ.get('pylons.routes_dict')
        if routes.get('controller') == 'package' \
            and routes.get('action') == 'read':
                for vocab in ('themeTaxonomy_available', 'theme_available', 'frequences_available', ):
                    try:
                        vocab_tags = c.pkg_dict.get(vocab, [])
                    except NotFound:
                        vocab_tags = None
			
                    if not vocab_tags:
                        continue

                    html = '<li class="sidebar-section">'
                    if vocab == 'frequences_available':
                        html = html + '<h3>Fr&eacute;quence</h3>'
                    elif vocab == 'themeTaxonomy_available':
                        html = html + '<h3>Th&egrave;mes</h3>'
                    html = html + '<ul class="tags clearfix">'
                    for tag in vocab_tags:
                        html = html + '<li>%s</li>' % tag.encode('ascii', 'xmlcharrefreplace')
                    html = html + "</ul></li>"
                    stream = stream | Transformer(
                        "//div[@id='sidebar']//ul[@class='widget-list']"
                    ).append(HTML(html))
		try:
			'''Get id in the table and convert it to readable name'''	
			publisher = base.model.Group.get(c.pkg_dict.get('dct:publisher'))
			if publisher : 
				html_bis = '<td class="dataset-details" property="rdf:value">%s</td>' % publisher.title
				stream = stream | Transformer(
				        "//tr[@id='dct:publisher']//td[@class='dataset-details']"
				    ).replace(HTML(html_bis))
			else :
				stream = stream
		except NotFound:
			stream = stream
        return stream

    '''the IAction extension returns a dictionary of core actions it wants to override.'''
    def get_actions(self):
        return {'my_vocabulary_show': my_vocabulary_show}
