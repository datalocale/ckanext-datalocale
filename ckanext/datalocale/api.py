import os
import pylons
from pylons import config
import logging
import ckan.authz as authz
import ckan.logic as logic
from ckan.logic import get_action, NotFound, NotAuthorized, check_access
from ckan.lib import base
from ckan.lib.base import c, model
import ckan.lib.plugins
import ckan.plugins
from ckan.plugins import implements, SingletonPlugin
from ckan.plugins import IActions, IRoutes
from ckanext.datalocale import forms
log = logging.getLogger(__name__)

class DatalocaleAPI(SingletonPlugin):
    """
      - ``IActions`` Allow adding of actions to the logic layer (API).
    """

    implements(IActions, inherit=True)

    implements(IRoutes)

    def before_map(self, map):
	'''Fix a ckanext-organization bug'''
        map.redirect('/organization/publisher_read', '/organization/organization_read')
        return map

    def after_map(self, map):
        return map

    '''the IAction extension returns a dictionary of core actions it wants to override.'''
    def get_actions(self):
        return {'datalocale_vocabulary_show': datalocale_vocabulary_show,
		'datalocale_vocabulary_list': datalocale_vocabulary_list,
		'package_show_rest' : datalocale_package_show_rest,
		'datalocale_package_show' : datalocale_package_show,
		'datalocale_group_show' : datalocale_group_show,
		'group_show_rest' : datalocale_group_show,
		'datalocale_tag_list' : datalocale_tag_list,
		'user_create' : datalocale_user_create,
		'datalocale_package_list' : datalocale_package_list,
		'datalocale_show_roles' : datalocale_show_roles,
		'datalocale_role_user' : datalocale_role_user,
	}

"""
    datalocale_vocabulary_show 
	id : Vocabulary id
	recursive : If true, get the child vocabulary (deprecated)
"""
def datalocale_vocabulary_show(context, data_dict):
    context['for_view'] = True
    vocab_list = logic.action.get.vocabulary_show(context, data_dict)
    if data_dict.get('recursive'):
	tags_list = []
	for vocab in vocab_list['tags']:
	    data = {'id': vocab['name']}
	    tag_list = logic.action.get.vocabulary_show(context, data)
	    tags_list.append(tag_list)
	return tags_list
    else:
	return vocab_list

def datalocale_vocabulary_list(context, data_dict):
    data = {'vocabulary_id': data_dict['id']}
    vocab_list = get_action('tag_list')(context, data)
    lang = pylons.request.environ['CKAN_LANG']
    lang_fallback = pylons.config.get('ckan.locale_default', 'fr')
    if data_dict.get('recursive'):
	    results = []
	    for vocab in vocab_list : 
	    	try:
		    tags = logic.get_action('tag_list')(context, {'vocabulary_id': vocab})
		    tag_translations = forms._translate(tags, lang, lang_fallback)
		    result = [(t, tag_translations[t]) for t in tags]
		    results.append(result)
		except logic.NotFound:
		    log.fatal('Vocabulary NotFound')
	    return results
    else:
	tag_translations = forms._translate(vocab_list, lang, lang_fallback)
	result = [(t, tag_translations[t]) for t in vocab_list]
	return result

def datalocale_tag_list(context, data_dict):
    context['for_view'] = True
    return logic.action.get.tag_list(context, data_dict)

def datalocale_package_show(context, data_dict):
    ckan_lang = pylons.request.environ['CKAN_LANG']
    ckan_lang_fallback = pylons.config.get('ckan.locale_default', 'fr')
    package = logic.get_action('package_show')(context, data_dict)
    theme_available = package.get('theme_available', [])
    themeTaxonomy = package.get('themeTaxonomy', [])
    package['themeTaxonomy'] = forms._translate(theme_available , ckan_lang, ckan_lang_fallback);
    package['theme_available'] = forms._translate(themeTaxonomy , ckan_lang, ckan_lang_fallback); 
    ''' Find extras that are not part of our schema '''
    # find extras that are not part of our schema
    additional_extras = []
    schema_keys = forms.DatalocaleDatasetForm.form_to_db_schema(forms.DatalocaleDatasetForm()).keys()
    extras = package.get('extras', [])
    for extra in extras:
      if not extra['key'] in schema_keys:
        additional_extras.append(extra)
    package['additional_extras'] = additional_extras
    return package;

def datalocale_package_show_rest(context, data_dict):
    return datalocale_package_show(context, data_dict)

def datalocale_group_show(context, data_dict): 
    groups = logic.get_action('group_show')(context, data_dict)
    group = base.model.Group.get(data_dict['id'])
    children = group.get_children_groups('organization')
    parent = group.get_groups('organization')
    if parent and parent[0] : 
	    groups['parent'] = [ { "id": parent[0].id, "name": parent[0].name, "title": parent[0].title, "description": parent[0].description, 
		"type": parent[0].type, "image_url": parent[0].image_url, "approval_status": parent[0].approval_status, 
		"state": parent[0].state, "revision_id": parent[0].revision_id}]
    return groups

def datalocale_user_create(context, data_dict):
    from ckan.lib.navl.validators import not_empty
    from validators import email_validator
    schema = context.get('schema')
    schema.update({
        'email': [not_empty, unicode, email_validator],
    })
    context['schema'] = schema
    logic.action.create.user_create(context, data_dict)



_check_access = logic.check_access
def datalocale_package_list(context, data_dict):
    '''Return a list of the names of the site's datasets (packages). :rtype: list of strings
    '''
    model = context["model"]
    api = context.get("api_version", 1)
    ref_package_by = 'id' if api == 2 else 'name'

    _check_access('package_list', context, data_dict)

    query = model.Session.query(model.Package)
    query = query.filter(model.Package.state=='active')
    packages = query.all()
    packages_to_import = []
    #Check if visitor can read the package
    authorizer = ckan.authz.Authorizer()
    action = model.Action.READ 
    for p in packages:
	if p.is_private == False and authorizer.is_authorized(u'visitor', action, p):
		   packages_to_import.append(p)
    return [getattr(p, ref_package_by) for p in packages_to_import]

def datalocale_show_roles(context, data_dict):
        import ckan.model as model
	p = base.model.Package.get(data_dict['id'])
        q = model.Session.query(model.PackageRole)
        q = q.filter_by(package=p)
	q.all()
	return [({"package_id":role.package_id,"user_id":role.user_id,"role":role.role}) for role in q]

def datalocale_role_user(context,data_dict):
	import ckan.model as model
	u = base.model.User.get(data_dict['id'])
	q = model.Session.query(model.UserObjectRole)
	q = q.filter_by(user_id=u.id)
	q = q.filter_by(context="System")
	q.all()
	if q.count() == 0:
	   return [({"user_id":u.id,"role":"None","context":"System"})]
	else: 
	   return [({"user_id":role.user_id,"role":role.role,"context":role.context}) for role in q]
