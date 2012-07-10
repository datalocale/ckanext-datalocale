import ckan.logic as logic
import ckan.lib.navl.dictization_functions as df
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
	''' 
	Add data[key] as the first group name in data
	'''
	def convert(key, data, errors, context):
		data[('groups', num, field)] = data[key]
	return convert

def convert_from_groups(field, num):
	'''
	Set data[key] to the first group name in data (if any exist).
	'''
	def convert(key, data, errors, context):
		data[key] = data.get(('groups', num, field), None)
	return convert

def convert_from_groups_extra(field, num):
	'''
	Set data[key] to the first group name in data (if any exist).
	'''
	def convert(key, data, errors, context):
	    value = data.get(('groups', num, field), None)
	    extra_number = 0
	    for k in data.keys():
		if k[0] == 'extras':
		    extra_number = max(extra_number, k[1] + 1)
            data[('extras', extra_number, 'key')] = key[0]
            if not context.get('extras_as_string'):
		data[('extras', extra_number, 'value')] = json.dumps(value)
	    else:
		data[('extras', extra_number, 'value')] = value
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
