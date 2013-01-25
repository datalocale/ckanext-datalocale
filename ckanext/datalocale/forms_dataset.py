import os
import pylons
import re
from pylons import config
from pylons.i18n import _
import logging
import ckan.authz as authz
import ckan.logic as logic
from ckan.logic import get_action, NotFound, NotAuthorized, check_access
from ckan.lib.base import request, c, BaseController, model, abort, h, g, render
from ckan.lib import base
from ckan.lib.base import c, model
from ckan.plugins import IDatasetForm, IGroupForm, IConfigurer, IGenshiStreamFilter, IRoutes
from ckan.plugins import implements, SingletonPlugin
import ckan.lib.plugins
import ckan.plugins
import ckan.logic.schema as default_schema
from ckan.lib.navl.validators import ignore_missing, ignore_empty, keep_extras, not_empty, ignore, default
from ckan.logic.converters import convert_to_extras, convert_from_extras, convert_to_tags, convert_from_tags, free_tags_only
from converters import datalocale_convert_from_tags, datalocale_convert_to_tags, \
convert_to_groups, convert_from_groups_visibility, date_to_db, \
extract_other, use_other, get_score
from pylons import request
from genshi.filters import Transformer
from genshi.input import HTML
from commands import VOCAB_FREQUENCY, VOCAB_THEMES, VOCAB_THEMES_CONCEPT, VOCAB_DATAQUALITY, VOCAB_GEOGRAPHIC_GRANULARITY, VOCAB_REFERENCES
log = logging.getLogger(__name__)
from routes import Mapper



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
            translation = logic.get_action('term_translation_show')({'model': model},{'terms': [term], 'lang_codes': [fallback_lang]})
            if translation:
                term_translations[term] = translation[0]['term_translation']
            else:
                term_translations[term] = term
    return term_translations

def datalocale_vocabulary_list(context, data_dict):
    data = {'vocabulary_id': data_dict['id']}
    vocab_list = get_action('tag_list')(context, data)
    lang = pylons.request.environ['CKAN_LANG']
    lang_fallback = pylons.config.get('ckan.locale_default', 'fr')
    if data_dict.get('recursive'):
        results = []
        for vocab in vocab_list : 
            try:
                tags = get_action('tag_list')(context, {'vocabulary_id': vocab})
                tag_translations = _translate(tags, lang, lang_fallback)
                result = [(t, tag_translations[t]) for t in tags]
                results.append(result)
            except NotFound:
                log.fatal('Vocabulary NotFound')
        return results
    else:
        tag_translations = _translate(vocab_list, lang, lang_fallback)
        result = [(t, tag_translations[t]) for t in vocab_list]
        return result
    
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
    implements(IRoutes)

    def before_map(self, map):
     
            controller = 'ckanext.datalocale.datalocale_storage:DatalocaleStorageController'
            controller_dataset = 'ckanext.datalocale.dataset_controllers:DatalocaleDatasetController'
            controller_storage = 'ckanext.datalocale.storage_controllers:DatalocaleStorageController'
            controller_package = 'package'
            
            map.connect('/storage/datalocale_upload_handle', action='upload_handle', controller=controller_storage)
            map.connect('/dataset/search', controller=controller_package, action='search')
            map.connect('/dataset/{action}', controller=controller_dataset,
            requirements=dict(action='|'.join([
                  'list',
                  'new',
                  'autocomplete',
                  ]))
              )
    
            map.connect('/dataset/{action}/{id}/{revision}', controller=controller_dataset, action='read_ajax',
              requirements=dict(action='|'.join([
              'read',
              'edit',
              'authz',
              'history',
              ]))
            )
            map.connect('/dataset/{action}/{id}', controller=controller_dataset,
              requirements=dict(action='|'.join([
              'edit',
              'editresources',
              'authz',
              'history',
              'read_ajax',
              'history_ajax',
              ]))
              )
            map.connect('/dataset/{id}.{format}', action='read', controller=controller_dataset)
            map.connect('/dataset/{id}', action='read', controller=controller_dataset)
            map.connect('/dataset/{id}/resource/{resource_id}', action='resource_read', controller=controller_dataset)
            map.connect('/dataset/{id}/resource/{resource_id}/embed', action='resource_embedded_dataviewer', controller=controller_dataset)
            
            return map

    def after_map(self, map):
        return map
    
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
        import uuid
        ckan_lang = pylons.request.environ['CKAN_LANG']
        ckan_lang_fallback = pylons.config.get('ckan.locale_default', 'fr')
        c.groups_available = c.userobj and c.userobj.get_groups('organization') or []
        c.licences = [('', '')] + ckan.model.Package.get_license_options()
        c.is_sysadmin = authz.Authorizer().is_sysadmin(c.user)
        c.resource_columns = model.Resource.get_columns()
        c.publishers_available = c.groups_available
        c.creators_available = c.userobj and c.userobj.get_groups('service') or []
        c.contributor = c.userobj
        c.frequency_available = commands.tags_frequency
        c.dataQuality_available = commands.tags_dataQuality
        c.temporal_granularity_available = commands.tags_temporal_granularity
        c.geographic_granularity_available = commands.tags_geographic_granularity
        c.key_upload = config.get('ckan.storage.key_prefix', 'file/') + request.params.get('filepath', str(uuid.uuid4()))
        try : 
            if c.pkg_dict: 
                if c.pkg_dict.get('dct:publisher', ''): 
                    c.current_publisher = logic.get_action('group_show')(context, {'id':c.pkg_dict.get('dct:publisher','').replace('\\', '').replace('"', '')}) 
        except NotFound:
            c.current_publisher = None
        try:
            if c.pkg_dict :  
                if c.pkg_dict.get('dct:creator', ''): 	
                    c.current_creator = logic.get_action('group_show')(context, {'id':c.pkg_dict.get('dct:creator','').replace('\\', '').replace('"', '')})
        except NotFound : 
            c.current_creator = None
        try:
            c.themeTaxonomy_available = _tags_and_translations(context, VOCAB_THEMES, ckan_lang, ckan_lang_fallback)
        except NotFound:
            c.themeTaxonomy_available = []
            pass
        ''' Find extras that are not part of our schema '''
        c.additional_extras = []
        schema_keys = self.form_to_db_schema().keys()
        if c.pkg_dict:
            extras = c.pkg_dict.get('extras', [])
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
        '''try:
            if c:
                if c.userobj : 
                    ckan_author_default = c.userobj.id
                else : 
                    ckan_author_default = ""
        except NotFound:
            ckan_author_default = ""
            pass'''
        schema = default_schema.package_form_schema()
        schema.update({
        'metadata_created' : [ignore_missing],
		'ckan_author': [unicode, convert_to_extras],
		'dct:contributor': [unicode, ignore_missing, convert_to_extras],
		'dct:publisher': [convert_to_groups('id', 0), convert_to_extras],
        'dct:creator': [convert_to_groups('id', 1), convert_to_extras],
		'capacity': [default(u'private'), convert_to_groups('capacity', 0),  convert_to_groups('capacity', 1)],
		'themeTaxonomy': [ignore_missing, convert_to_tags(VOCAB_THEMES)],
		'theme_available': [ignore_missing, datalocale_convert_to_tags('themeTaxonomy')],
		'dataQuality': [ignore_missing, convert_to_tags(VOCAB_DATAQUALITY)],
		'dct:accrualPeriodicity': [use_other, ignore_missing, convert_to_extras],
		'dct:accrualPeriodicity-other': [],
		'temporal_coverage-from': [ignore_missing, date_to_db, convert_to_extras],
		'temporal_coverage-to': [ignore_missing, date_to_db, convert_to_extras],
		'geographic_granularity': [use_other, convert_to_extras],
		'geographic_granularity-other': [],
		'spatial': [ignore_empty, convert_to_extras],
		'spatial-text': [ignore_empty, unicode,  convert_to_extras],
		'spatial-uri': [ignore_empty, unicode, convert_to_extras],
		'dcat:granularity': [ignore_missing, unicode, convert_to_extras],
		'dcterms:references': [ignore_missing, unicode, convert_to_extras],
		'dc:source': [ignore_missing, unicode, convert_to_extras],
		'maj': [ignore_missing, unicode, convert_to_extras],
		'resources': default_schema.default_resource_schema(),
		'image_url': [ignore_missing, convert_to_extras]
    	})
        schema['groups'].update({
            'capacity': [ignore_missing, unicode],
            'id': [ignore_missing],
            'name': [],
            'title': [ignore_missing]
        })
        return schema


    def db_to_form_schema_options(self, options):
        schema = self.db_to_form_schema()
        try:
            routes = request.environ.get('pylons.routes_dict')
            controller_dataset = 'ckanext.datalocale.dataset_controllers:DatalocaleDatasetController'
            if options.get('type') == 'show' and options.get('api') == False:
                if (routes.get('controller') == 'package' or routes.get('controller') == controller_dataset) and routes.get('action') == 'read':
                    context = options.get('context')
                    package = context.get('package')
                    package_dict = logic.get_action('datalocale_package_show')({'model': model, 'api_version':'3', 'user':context.get('user')} ,{'id' : package.id })
                    try:
                        if len(package_dict.get('themeTaxonomy').keys()) > 0:
                            themeTaxonomy_url = package_dict.get('themeTaxonomy').keys()[0]
                            theme_url = package_dict.get('theme_available').keys()[0]
                            themeTaxonomy_name = package_dict.get('themeTaxonomy').get(themeTaxonomy_url)
                            theme_name = package_dict.get('theme_available').get(theme_url)
                            tag_themeTaxonomy = logic.get_action('tag_search')({'model': model, 'api_version':'3', 'user':context.get('user')} ,{'query' : themeTaxonomy_url, 'vocabulary_id': 'dcat:themeTaxonomy'})
                            tag_theme = logic.get_action('tag_search')({'model': model, 'api_version':'3', 'user':context.get('user')} ,{'query' : theme_url, 'vocabulary_id': themeTaxonomy_url})
                            if  tag_themeTaxonomy.get('results') :
                                c.tag_themeTaxonomy = tag_themeTaxonomy.get('results')[0]
                                c.tag_theme = tag_theme.get('results')[0]
                                c.tag_themeTaxonomy['title'] = themeTaxonomy_name
                                c.tag_theme['title'] = theme_name
                    except (logic.NotFound, IndexError) as e:
                        pass
                    coords = re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", package_dict.get("spatial"))
                    c.bbox = "{minLng}%2C{minLat}%2C{maxLng}%2C{MaxLat}".format(minLng = coords[0].strip(),minLat = coords[5].strip(),maxLng = coords[2].strip(),MaxLat = coords[1].strip() )
        except:
            pass
        return schema

    def db_to_form_schema(self, package_type=None):
        """
        Returns the schema for mapping package data from the database into a
        format suitable for the form (optional)
        """
        import commands
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
		'isopen' : [ignore_missing],
		'state' : [ignore_missing],
		'notes': [ignore_missing, unicode],
		'type': [unicode],
		'tags': {'__extras': [keep_extras, free_tags_only]},
		'ckan_author': [convert_from_extras, ignore_missing],
		'dct:publisher': [convert_from_extras, ignore_missing],
		'dct:creator': [convert_from_extras, ignore_missing],
		'capacity': [convert_from_groups_visibility('capacity')],
		'dct:contributor': [convert_from_extras, ignore_missing],
		'themeTaxonomy': [convert_from_tags(VOCAB_THEMES), ignore_missing],
		'theme_available': [datalocale_convert_from_tags('themeTaxonomy'), ignore_missing],
		'dataQuality': [convert_from_tags(VOCAB_DATAQUALITY), ignore_missing],
		'dct:accrualPeriodicity': [convert_from_extras, ignore_missing, extract_other(commands.tags_frequency)],
		'temporal_coverage-from': [convert_from_extras, ignore_missing],
		'temporal_coverage-to': [convert_from_extras, ignore_missing],
		'geographic_granularity': [convert_from_extras, ignore_missing, extract_other(commands.tags_geographic_granularity)],
		'spatial': [convert_from_extras, ignore_missing],
		'spatial-text': [convert_from_extras, ignore_missing],
		'spatial-uri': [convert_from_extras, ignore_missing],
		'dcat:granularity': [convert_from_extras, ignore_missing],
		'dcterms:references': [convert_from_extras, ignore_missing],
		'dc:source': [convert_from_extras, ignore_missing],
		'maj': [convert_from_extras, ignore_missing],
		'resources': default_schema.default_resource_schema(),
		'openness_score': [get_score('openness_score'), ignore_missing],
		'image_url': [convert_from_extras, ignore_missing],
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
        '''Check if the return data is correct, mostly for checking out if spammers are submitting only part of the form'''
        return

    def filter(self, stream):
        ''' Add vocab tags to the bottom of the sidebar.'''
        routes = request.environ.get('pylons.routes_dict')
        controller_dataset = 'ckanext.datalocale.dataset_controllers:DatalocaleDatasetController'
        controller_tag = 'tag'
        if ((routes.get('controller') == 'package' or routes.get('controller') == controller_dataset) and routes.get('action') == 'read'):
            try:
                themeTaxonomy = c.pkg_dict.get('themeTaxonomy', [])[0]
                theme_available = c.pkg_dict.get('theme_available', [])[0]
                
                ThemeId = str(c.tag_themeTaxonomy.get('name'))
                ThemeName = str(themeTaxonomy.encode('ascii', 'xmlcharrefreplace'))
                
                html = '<li class="sidebar-section"><h3>' + ('Th&egrave;me') + '</h3><ul class="tags clearfix">'\
                    '<li><a href="{site_url}/dataset?themes={themeT_id}">{themeT_title}</a></li></ul>' . format(site_url=c.site_url, themeT_id = ThemeId, themeT_title = ThemeName)
                    
                html +=    '<h3>' + ('Sous Th&egrave;me') + '</h3><ul class="tags clearfix"><li><a href="{site_url}/dataset?sous_themes={theme_id}">{theme_title}</li></ul></li>'.format(themeT_title = ThemeName, theme_title = theme_available.encode('ascii', 'xmlcharrefreplace'), site_url=c.site_url, themeT_id = ThemeId, theme_id= c.tag_theme.get('name'))

                stream = stream | Transformer(
                    "//div[@id='sidebar']//ul[@class='widget-list']//li[@class='themes_sous_themes']"
                ).replace(HTML(html))
            except (NotFound, IndexError) as e:
                pass   
            try:
                '''Get id in the table and convert it to readable name'''
                publisher = c.pkg_dict.get('dct:publisher','')
                creator = c.pkg_dict.get('dct:creator','')
                rdfPublisher = ""
                rdfCreator = ""
                if c.pkg_dict.get('groups') :
                    for group in c.pkg_dict.get('groups') : 
                        group_id = group.get('id')
                        div = ""
                        if group_id == publisher:
                            div = 'dct:publisher' 
                            rdfCreator = '<dct:publisher rdf:about="%s/diffuseur/%s">' % (c.site_url, group.get('name', ''))
                            rdfCreator +=        '<rdf:Description> \
                                             <foaf:name>' + group.get('title', '') + '</foaf:name> \
                                             <foaf:mbox rdf:resource="mailto:' + group.get('mail', '')+ '"></foaf:mbox>\
                                       </rdf:Description>\
                                  </dct:publisher>'
                            html_bis = '<td class="dataset-details" property="rdf:value"><a href="%s/diffuseur/%s">%s</a></td>' % (c.site_url, group.get('name', ''), group.get('title', ''))
                            if div:
                              stream = stream | Transformer("//tr[@id='%s']//td[@class='dataset-details']" % div).replace(HTML(html_bis))
               
                        if group_id == creator: 
                            div = 'dct:creator'
                            rdfPublisher = '<dct:creator rdf:about="%s/producteur/%s">'% (c.site_url, group.get('name', ''))
                            rdfPublisher += '<rdf:Description> \
                                             <foaf:name>' + group.get('title', '') + '</foaf:name> \
                                             <foaf:mbox rdf:resource="mailto:' + group.get('mail', '')+ '"></foaf:mbox>\
                                       </rdf:Description>\
                                  </dct:creator>' 
                            html_bis = '<td class="dataset-details" property="rdf:value"><a href="%s/producteur/%s">%s</a></td>' % (c.site_url, group.get('name', ''), group.get('title', ''))
                        
                        if div:
                            stream = stream | Transformer("//tr[@id='%s']//td[@class='dataset-details']" % div).replace(HTML(html_bis))
  
                            
                    if rdfPublisher != "": 
                        stream = stream | Transformer('//publisher').replace(HTML(rdfPublisher))
                    if rdfCreator != "":
                        stream = stream | Transformer('//creator').replace(HTML(rdfCreator))
            except NotFound:
                stream = stream
        if routes.get('controller') == 'user' and routes.get('action') == 'read':	
            user = base.model.User.get(c.id)
            groups = user.get_groups()
            html = "<dt>" + _('Diffuseur') + "</dt><dd>"
            for group in groups :
                html += "<a href='" + h.url_for('/diffuseur/') +  group.name + "' class='label' style='color:white'>"+group.title+"</a> "
            html += "</dd>"
            stream = stream | Transformer("//div[@id='content']//dl[@class='vcard']").append(HTML(html))
            
        if routes.get('controller') == controller_tag and routes.get('action') == 'index' and request.params.get('themes', '') == 'true':
            context = {'model': model, 'session': model.Session,            
            'user': c.user or c.author, 'for_view': True}
            q = {}
            fq = ''
            data_dict = {
                'q':q,
                'fq':fq,
                'facet.field':g.facets,
            }

	    context['ignore_capacity_check'] = True
            query = get_action('package_search')(context,data_dict)
            c.facets = query['facets']
            c.search_facets = query['search_facets']
            
 
            
            # FACETS THEMES / SOUS THEMES
            #
            #
            #
            ckan_lang = pylons.request.environ['CKAN_LANG']
            ckan_lang_fallback = pylons.config.get('ckan.locale_default', 'fr')
            themesFacet = {'title':'themes', 'items' : []}
            sousThemesFacet = {'title':'sous_themes', 'items' : []}
            tagsFacet = {'title':'tags', 'items' : []}
            try:
                themes = _tags_and_translations(context, VOCAB_THEMES, ckan_lang, ckan_lang_fallback)
                sous_themes = []
                for key, value in themes:
                    data_dict = {"id": key}
                    sous_themes.append(datalocale_vocabulary_list(context, data_dict))
                for tag in c.search_facets[u"tags"]["items"]:
                    is_theme_or_sstheme = False
                    for theme in themes:
                        if theme[0] == tag["name"]:
                            tagJson = {'name' : theme[0], 'display_name' : theme[1], 'count' : tag["count"]}
                            themesFacet["items"].append(tagJson)
                            is_theme_or_sstheme = True
                    for sous_theme in sous_themes:
                        for sous_theme_couple in sous_theme:
                            if sous_theme_couple[0] == tag["name"]:
                                tagJson = {'name' : sous_theme_couple[0], 'display_name' : sous_theme_couple[1], 'count' : tag["count"]}
                                sousThemesFacet["items"].append(tagJson)
                                is_theme_or_sstheme = True
                    if is_theme_or_sstheme == False:
                        tagJson = {'name' : tag["name"], 'display_name' : tag["display_name"], 'count' : tag["count"]}
                        tagsFacet["items"].append(tagJson)
                c.search_facets[u"themes"] = themesFacet
                c.search_facets[u"sous_themes"] = sousThemesFacet
                c.search_facets[u"tags"] = tagsFacet
            except NotFound:
                sys.stderr.write("NotFound")  
            
            loop = False
            html = u'<h2>' + _('Themes') + '</h2><br/><div id="themesCloudDiv" style="width: 450px; height: 600px;margin:auto;overflow:visible;"></div>'
            html += '<script type="text/javascript"> var word_array = ['
            for theme in c.search_facets[u"themes"]["items"]:
                if loop:
                    html += ','
                else:
                    loop = True
                html += '{text: "' + theme["display_name"] + '", weight: 10, link: "/dataset?themes=' + theme["name"] + '"}'
            for stheme in c.search_facets[u"sous_themes"]["items"]:
                if loop:
                    html += ','
                html += '{text: "' + stheme["display_name"] + '", weight: 5, link: "/dataset?sous_themes=' + stheme["name"] + '"}'
            html += '];'
            html += '</script>'
            stream = stream | Transformer("//div[@class='container']//div[@id='content']//div").replace(HTML(html))
        return stream

   

