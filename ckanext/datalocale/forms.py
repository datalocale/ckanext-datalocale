import os
import pylons
from pylons import config
import logging
import ckan.authz as authz
import ckan.logic as logic
from ckan.logic import get_action, NotFound, NotAuthorized, check_access
from ckan.lib import base
from ckan.lib.base import c, model, abort, request
from ckan.plugins import IDatasetForm, IGroupForm, IConfigurer, IGenshiStreamFilter, IActions
from ckan.plugins import implements, SingletonPlugin
import ckan.lib.plugins
import ckan.plugins
from ckan.logic.schema import package_form_schema, default_resource_schema
from ckan.lib.navl.validators import ignore_missing, keep_extras, not_empty, ignore
from ckan.logic.converters import convert_to_extras,\
    convert_from_extras, convert_to_tags, convert_from_tags, free_tags_only
from validators import datalocale_convert_from_tags, datalocale_convert_to_tags

log = logging.getLogger(__name__)

VOCAB_FREQUENCES = u'dct:accrualPeriodicity'
VOCAB_THEMES = u'dcat:themeTaxonomy'
VOCAB_THEMES_CONCEPT = u'dcat:theme'
VOCAB_DATAQUALITY = u'dcat:dataQuality'
VOCAB_GRANULARITY = u'dcat:granularity'
VOCAB_REFERENCES = u'dcterms:references'

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


    """
    implements(IDatasetForm, inherit=True)
    implements(IConfigurer, inherit=True)
    implements(IGenshiStreamFilter, inherit=True)


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

    def package_types(self):
        return ["dataset"]

    def is_fallback(self):
        return True

    def setup_template_variables(self, context, data_dict, package_type=None):
	''' Translation '''
	ckan_lang = pylons.request.environ['CKAN_LANG']
	ckan_lang_fallback = pylons.config.get('ckan.locale_default', 'fr')
        c.groups_available = c.userobj and c.userobj.get_groups('organization') or []
        c.licences = [('', '')] + base.model.Package.get_license_options()
        c.is_sysadmin = authz.Authorizer().is_sysadmin(c.user)
	c.publishers_available = c.groups_available
	c.creators_available = c.userobj and c.userobj.get_groups('service') or []
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
    	try:
		data = {'vocabulary_id': VOCAB_DATAQUALITY}
		c.dataQuality_available = get_action('tag_list')(context, data)
	except NotFound:
		c.dataQuality_available = []
    	try:
		data = {'vocabulary_id': VOCAB_GRANULARITY}
		c.granularity_available = get_action('tag_list')(context, data)
	except NotFound:
		c.granularity_available = []
	
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
    	schema = package_form_schema()
    	schema.update({
        	'frequencies': [ignore_missing, convert_to_tags(VOCAB_FREQUENCES)],
		'themeTaxonomy': [ignore_missing, convert_to_tags(VOCAB_THEMES)],
		'theme_available': [ignore_missing, datalocale_convert_to_tags('themeTaxonomy')],
		'dataQuality': [ignore_missing, convert_to_tags(VOCAB_DATAQUALITY)],
		'granularity': [ignore_missing, convert_to_tags(VOCAB_GRANULARITY)],
		'dct:creator': [unicode, convert_to_extras, ignore_missing],
		'dct:publisher': [unicode, convert_to_extras, ignore_missing],
		'dct:contributor': [unicode, convert_to_extras, ignore_missing],
		'dct:temporal': [unicode, convert_to_extras, ignore_missing],
		'dc:source': [unicode, convert_to_extras, ignore_missing],
		'maj': [unicode, convert_to_extras, ignore_missing],
		'dcterms:references': [unicode, convert_to_extras, ignore_missing],
    	})
        schema['groups'].update({
            'capacity': [ignore_missing, unicode]
        })
        return schema


    def db_to_form_schema_options(self, options):
        schema = self.db_to_form_schema()
        return schema

    def db_to_form_schema(self, package_type=None):
        """
        Returns the schema for mapping package data from the database into a
        format suitable for the form (optional)
        """
	schema = package_form_schema()
        schema['groups'].update({
	    'id': [ignore_missing],
            'name': [ignore_missing, unicode],
            'title': [ignore_missing],
            'capacity': [ignore_missing, unicode]
        })
    	schema.update({
		'id' : [ignore_missing],
		'revision_id' : [ignore_missing],
		'metadata_created' : [ignore_missing],
		'metadata_modified' : [ignore_missing],
		'state' : [ignore_missing],
		'notes': [ignore_missing, unicode],
		'type': [unicode],
		'tags': {'__extras': [keep_extras, free_tags_only]},
		'frequencies': [convert_from_tags(VOCAB_FREQUENCES), ignore_missing],
		'themeTaxonomy': [convert_from_tags(VOCAB_THEMES), ignore_missing],
		'theme_available': [datalocale_convert_from_tags('themeTaxonomy'), ignore_missing],
		'dataQuality': [convert_from_tags(VOCAB_DATAQUALITY), ignore_missing],
		'granularity': [convert_from_tags(VOCAB_GRANULARITY), ignore_missing],
		'dct:creator': [convert_from_extras, ignore_missing],
		'dct:publisher': [convert_from_extras, ignore_missing],
		'dct:contributor': [convert_from_extras, ignore_missing],
		'dct:temporal': [convert_from_extras, ignore_missing],
		'dc:source': [convert_from_extras, ignore_missing],
		'maj': [convert_from_extras, ignore_missing],
		'isopen' : [ignore_missing],
		'dcterms:references': [convert_from_extras, ignore_missing],
    	})
	schema['resources'].update({
            'created': [ignore_missing],
            'position': [not_empty],
            'last_modified': [ignore_missing],
            'cache_last_updated': [ignore_missing],
            'webstore_last_updated': [ignore_missing]
        })	
        return schema

    def check_data_dict(self, data_dict):
        '''Check if the return data is correct, mostly for checking out
	if spammers are submitting only part of the form'''
	return

    def filter(self, stream):
        ''' Add vocab tags to the bottom of the sidebar.'''
        from pylons import request
        from genshi.filters import Transformer
        from genshi.input import HTML
        routes = request.environ.get('pylons.routes_dict')
        if routes.get('controller') == 'package' \
            and routes.get('action') == 'read':
                for vocab in ('themeTaxonomy', 'theme_available', 'frequencies', ):
                    try:
                        vocab_tags = c.pkg_dict.get(vocab, [])
                    except NotFound:
                        vocab_tags = None
			
                    if not vocab_tags:
                        continue

                    html = '<li class="sidebar-section">'
                    if vocab == 'frequencies':
                        html = html + '<h3>Fr&eacute;quence</h3>'
                    elif vocab == 'themeTaxonomy':
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
			'''Get id in the table and convert it to readable name'''	
			creator = base.model.Group.get(c.pkg_dict.get('dct:creator'))
			if creator : 
				html_bis = '<td class="dataset-details" property="rdf:value">%s</td>' % creator.title
				stream = stream | Transformer(
				        "//tr[@id='dct:creator']//td[@class='dataset-details']"
				    ).replace(HTML(html_bis))
			else :
				stream = stream

		except NotFound:
			stream = stream

	if routes.get('controller') == 'group'\
            and routes.get('action') == 'read':	
		parents = c.group.get_groups('organization')
		html = ''
		if parents:
			parent = parents[0]
			html = html + '<li><h3>Parent</h3><ul class="no-break"><li>%s</li></ul></li>' % parent.name
		children = c.group.get_children_groups('organization')
		if children:
			html = html + '<li><h3>Groupes fils</h3><ul class="no-break">'
		for child in children :
			html = html + '<li>%s</li>' % child['title']
		if children:
			html = html + '</ul></li>'
		stream = stream | Transformer(
                        "//div[@id='sidebar']//ul[@class='widget-list']"
                    ).append(HTML(html))
        return stream

   

