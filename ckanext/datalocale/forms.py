import os
import pylons
from pylons import config
import logging
import ckan.authz as authz
import ckan.logic as logic
from ckan.logic import get_action, NotFound, NotAuthorized, check_access
from ckan.lib import base
from ckan.lib.base import c, model
from ckan.plugins import IDatasetForm, IGroupForm, IConfigurer, IGenshiStreamFilter, IActions
from ckan.plugins import implements, SingletonPlugin
import ckan.lib.plugins
import ckan.plugins
import ckan.logic.schema as default_schema
from ckan.lib.navl.validators import ignore_missing, ignore_empty, keep_extras, not_empty, ignore, default
from ckan.logic.converters import convert_to_extras, convert_from_extras, convert_to_tags, convert_from_tags, free_tags_only
from validators import datalocale_convert_from_tags, datalocale_convert_to_tags, convert_to_groups, convert_from_groups, convert_from_groups_extra, date_to_form, date_to_db

log = logging.getLogger(__name__)

VOCAB_FREQUENCY= u'dct:accrualPeriodicity'
VOCAB_THEMES = u'dcat:themeTaxonomy'
VOCAB_THEMES_CONCEPT = u'dcat:theme'
VOCAB_DATAQUALITY = u'dcat:dataQuality'
VOCAB_GEOGRAPHIC_GRANULARITY = u'geographic_granularity'
VOCAB_TEMPORAL_GRANULARITY = u'dct:temporal'
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
        return 'forms/dataset/dataset_form.html'

    def new_template(self):
        return 'package/new.html'

    def comments_template(self):
        return 'package/comments.html'

    def search_template(self):
        return 'package/search.html'

    def read_template(self):
        return 'forms/dataset/read.html'

    def history_template(self):
        return 'package/history.html'

    def package_types(self):
        return ["dataset"]

    def is_fallback(self):
        return True

    def setup_template_variables(self, context, data_dict, package_type=None):
	''' Translation '''
	import commands
	from pylons import request
	ckan_lang = pylons.request.environ['CKAN_LANG']
	ckan_lang_fallback = pylons.config.get('ckan.locale_default', 'fr')
        c.groups_available = c.userobj and c.userobj.get_groups('organization') or []
        c.licences = [('', '')] + base.model.Package.get_license_options()
        c.is_sysadmin = authz.Authorizer().is_sysadmin(c.user)
	c.resource_columns = model.Resource.get_columns()
	c.publishers_available = c.groups_available
	c.creators_available = c.userobj and c.userobj.get_groups('service') or []
	c.contributor = c.userobj
	'''c.frequency_available = get_action('tag_list')(context, {'vocabulary_id': VOCAB_FREQUENCY})'''
	c.frequency_available = commands.tags_frequency
	c.dataQuality_available = commands.tags_dataQuality
	c.temporal_granularity_available = commands.tags_temporal_granularity
	c.geographic_granularity_available = commands.tags_geographic_granularity
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
    	schema = default_schema.package_form_schema()
    	schema.update({
        	'dct:accrualPeriodicity': [ignore_missing, convert_to_tags(VOCAB_FREQUENCY)],
		'themeTaxonomy': [ignore_missing, convert_to_tags(VOCAB_THEMES)],
		'theme_available': [ignore_missing, datalocale_convert_to_tags('themeTaxonomy')],
		'dataQuality': [ignore_missing, convert_to_tags(VOCAB_DATAQUALITY)],
		'geographic_granularity': [ignore_missing, convert_to_tags(VOCAB_GEOGRAPHIC_GRANULARITY)],
		'dcat:granularity': [ignore_missing, unicode, convert_to_extras],
		'dct:creator': [convert_to_groups('name', 1)],
		'capacity': [ignore_missing, unicode, default(u'private'), convert_to_groups('capacity', 1),  convert_to_groups('capacity', 0)],
		'dct:publisher': [convert_to_groups('name', 0)],
		'dct:contributor': [unicode, ignore_missing, convert_to_extras],
		'ckan_author': [unicode, ignore_missing, convert_to_extras],
		'dct:temporal': [unicode, ignore_missing, ignore_empty, convert_to_tags(VOCAB_TEMPORAL_GRANULARITY)],
		'temporal_coverage-from': [ignore_missing, ignore_empty, date_to_db, convert_to_extras],
		'temporal_coverage-to': [ignore_missing, ignore_empty, date_to_db, convert_to_extras],
		'dc:source': [ignore_missing, ignore_empty, unicode, convert_to_extras],
		'maj': [unicode, ignore_missing, ignore_empty, convert_to_extras],
		'dcterms:references': [unicode, ignore_missing, ignore_empty, convert_to_extras],
		'resources': default_schema.default_resource_schema(),
		'spatial': [ignore_empty, convert_to_extras],
		'spatial-text': [ignore_empty, unicode,  convert_to_extras],
		'spatial-uri': [ignore_empty, unicode, convert_to_extras],
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
	schema = default_schema.package_form_schema()
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
		'revision_timestamp' : [ignore_missing],
		'state' : [ignore_missing],
		'notes': [ignore_missing, unicode],
		'type': [unicode],
		'tags': {'__extras': [keep_extras, free_tags_only]},
		'dct:accrualPeriodicity': [convert_from_tags(VOCAB_FREQUENCY), ignore_missing],
		'themeTaxonomy': [convert_from_tags(VOCAB_THEMES), ignore_missing],
		'theme_available': [datalocale_convert_from_tags('themeTaxonomy'), ignore_missing],
		'dataQuality': [convert_from_tags(VOCAB_DATAQUALITY), ignore_missing],
		'geographic_granularity': [convert_from_tags(VOCAB_GEOGRAPHIC_GRANULARITY), ignore_missing],
		'dcat:granularity': [convert_from_extras, ignore_missing],
		'dct:creator': [convert_from_groups('name', 1)],
		'dct:publisher': [convert_from_groups('name', 0)],
		'capacity': [convert_from_groups('capacity', 0), convert_from_groups('capacity', 1)],
		'dct:contributor': [convert_from_extras, ignore_missing],
		'ckan_author': [convert_from_extras, ignore_missing],
		'dct:temporal': [convert_from_tags(VOCAB_TEMPORAL_GRANULARITY), ignore_missing],
		'temporal_coverage-from': [convert_from_extras, ignore_missing],
		'temporal_coverage-to': [convert_from_extras, ignore_missing],
		'dc:source': [convert_from_extras, ignore_missing],
		'maj': [convert_from_extras, ignore_missing],
		'isopen' : [ignore_missing],
		'dcterms:references': [convert_from_extras, ignore_missing],
		'published_by': [convert_from_groups_extra('id', 0), ignore_missing],
		'created_by': [convert_from_groups_extra('id', 1), ignore_missing],
		'resources': default_schema.default_resource_schema(),
		'spatial': [convert_from_extras, ignore_missing],
		'spatial-text': [convert_from_extras, ignore_missing],
		'spatial-uri': [convert_from_extras, ignore_missing],
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
                for vocab in ('themeTaxonomy', 'theme_available' ):
                    try:
                        vocab_tags = c.pkg_dict.get(vocab, [])
                    except NotFound:
                        vocab_tags = None
			
                    if not vocab_tags:
                        continue

                    html = '<li class="sidebar-section">'
                    if vocab == 'themeTaxonomy':
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
		    if c.pkg_dict.get('groups') and c.pkg_dict.get('groups')[0]:	
			publisher = c.pkg_dict.get('groups')[0]
			if publisher : 
				html_bis = '<td class="dataset-details" property="rdf:value">%s</td>' % publisher.get('title', '')
				stream = stream | Transformer(
				        "//tr[@id='published_by']//td[@class='dataset-details']"
				    ).replace(HTML(html_bis))
			else :
				stream = stream
		    '''Get id in the table and convert it to readable name'''	
		    try: 
		      if c.pkg_dict.get('groups') and c.pkg_dict.get('groups')[1]:
			creator = c.pkg_dict.get('groups')[1]
			if creator : 
				html_bis = '<td class="dataset-details" property="rdf:value">%s</td>' % creator.get('title', '')
				stream = stream | Transformer(
				        "//tr[@id='created_by']//td[@class='dataset-details']"
				    ).replace(HTML(html_bis))
			else :
				stream = stream
		    except IndexError:
			pass

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

   

