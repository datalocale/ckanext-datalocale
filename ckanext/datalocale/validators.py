# -*-coding:utf-8 -*
import ckan.logic as logic
import ckan.lib.navl.dictization_functions as df
from ckan.lib.navl.dictization_functions import Invalid
import ckan.logic.validators as val
import ckan.model as model
import re

import logging
log = logging.getLogger(__name__)

try:
    import json
except ImportError:
    import simplejson as json

name_match = re.compile('[a-zA-Z0-9_\-]*$')


def datalocale_convert_from_tags(vocab):
    def callable(key, data, errors, context):
	n = data[(vocab,)]
	if n and n[0]:
		name = n[0]
		for k in data.keys():
		    if k[0] == 'tags':
		        if data[k].get('display_name') == name:
				vocabulary_name = data[k].get('name')
		if vocabulary_name:
			v = model.Vocabulary.get(vocabulary_name)
			if not v:
			    return
		else:
			return
		tags = []
		for k in data.keys():
		    if k[0] == 'tags':
		        if data[k].get('vocabulary_id') == v.id:
		            name = data[k].get('display_name', data[k]['name'])
		            tags.append(name)
		data[key] = tags
    return callable

def datalocale_convert_to_tags(vocab):
    def callable(key, data, errors, context):
	from ckan.logic.validators import tag_in_vocabulary_validator
	name = data[(vocab,)]
        new_tags = data.get(key)
        if not new_tags:
            return
        if isinstance(new_tags, basestring):
            new_tags = [new_tags]

        # get current number of tags
        n = 0
        for k in data.keys():
            if k[0] == 'tags':
                n = max(n, k[1] + 1)

	
        v = model.Vocabulary.get(name)
        if not v:
            return
        context['vocabulary'] = v

        for tag in new_tags:
            tag_in_vocabulary_validator(tag, context)

        for num, tag in enumerate(new_tags):
            data[('tags', num + n, 'name')] = tag
            data[('tags', num + n, 'vocabulary_id')] = v.id
    return callable

def convert_to_groups(field, num):
	def convert(key, data, errors, context):
		data[('groups', num, field)] = data[key]
	return convert

def convert_from_groups(field, num):
	def convert(key, data, errors, context):
		data[key] = data.get(('groups', num, field), None)
	return convert

def convert_from_groups_visibility(field):
	def convert(key, data, errors, context):
		data[key] = data.get(('groups', 0, field), None)
		if not data[key]: 
		   data[key] = data.get(('groups', 1, field), None)
	return convert

def email_validator(value, context):
    from ckan.lib.navl.dictization_functions import Invalid
    from pylons.i18n import _
    if len(value) > 7:
    	if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", value ) != None:
	    return value
    raise Invalid(_('Invalid email'))
    return value

def date_to_form(value, context):
    from ckan.lib.field_types import DateType, DateConvertError
    try:
        value = DateType.db_to_form(value)
    except DateConvertError, e:
        raise Invalid(str(e))
    return value

def date_to_db(value, context):
    from ckan.lib.field_types import DateType, DateConvertError
    try:
        value = DateType.form_to_db(value)
    except DateConvertError, e:
        raise Invalid(str(e))
    return value

def use_other(key, data, errors, context):
    other_key = key[-1] + '-other'
    other_value = data.get((other_key,), '').strip()
    if other_value:
        data[key] = other_value

def extract_other(option_list):
    def other(key, data, errors, context):
	from ckan.lib.navl.dictization_functions import missing
        value = data[key]
	if value : 
	   if type(value) is list:
	 	value = value[0]
	   else:
		value = value	
        if value in option_list:
	    if value ==  u'autre - merci de préciser' :
		data[key]= ""
            return
        elif value is missing:
            data[key] = ''
            return
        elif value == '':
            data[key] = ''
            return
        else:
            data[key] = u'autre - merci de préciser'
            other_key = key[-1] + '-other'
            data[(other_key,)] = value
    return other
