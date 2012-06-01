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
from ckan.plugins import IActions
import forms
log = logging.getLogger(__name__)

class DatalocaleAPI(SingletonPlugin):
    """
      - ``IActions`` Allow adding of actions to the logic layer (API).
    """

    implements(IActions, inherit=True)

    '''the IAction extension returns a dictionary of core actions it wants to override.'''
    def get_actions(self):
        return {'datalocale_vocabulary_show': datalocale_vocabulary_show,
		'datalocale_vocabulary_list': datalocale_vocabulary_list,
		'package_show_rest' : datalocale_package_show_rest,
		'datalocale_package_show' : datalocale_package_show,
		'datalocale_group_show' : datalocale_group_show,
		'group_show_rest' : datalocale_group_show,
		'datalocale_tag_list' : datalocale_tag_list,
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
    packages = logic.get_action('package_show')(context, data_dict)
    theme_available = packages.get('theme_available')
    themeTaxonomy = packages.get('themeTaxonomy')
    packages['themeTaxonomy'] = forms._translate(theme_available , ckan_lang, ckan_lang_fallback);
    packages['theme_available'] = forms._translate(themeTaxonomy , ckan_lang, ckan_lang_fallback); 
    return packages;

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

