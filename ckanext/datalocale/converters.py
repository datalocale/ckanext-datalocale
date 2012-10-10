# -*-coding:utf-8 -*
import ckan.logic as logic
from logic import NotFound
import ckan.lib.navl.dictization_functions as df
from ckan.lib.navl.dictization_functions import Invalid
import ckan.logic.validators
import ckan.model as model
import re
from ckan.lib.navl.dictization_functions import Invalid
from pylons.i18n import _

import logging
log = logging.getLogger(__name__)

try:
    import json
except ImportError:
    import simplejson as json

name_match = re.compile('[a-zA-Z0-9_\-]*$')


def datalocale_convert_from_tags(vocab):
    def callable(key, data, errors, context):
        try:
            n = data[(vocab,)]
        except:
            n = None
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

def convert_from_groups_visibility(field):
    def convert(key, data, errors, context):
        data[key] = data.get(('groups', 0, field), None)
        if not data[key]: 
            data[key] = data.get(('groups', 1, field), None)
    return convert

def get_score(field):
    def convert(key, data, errors, context):
        try:
            from ckanext.qa.reports import five_stars
            from ckanext.qa.html import get_star_html
            package_id = context['package'].id
            score_dict = five_stars(package_id)
            if score_dict : 
                score = score_dict[0].get(field)
                data[key] = int(score)
                data[('openness_score_html',)] = get_star_html(int(score), "")
        except NotFound, IndexError:
            pass
    return convert

def email_validator(value, context):
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
    try:
        other_value = data.get((other_key,), '').strip()
        if other_value:
            data[key] = other_value
    except:
        pass

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

def convert_to_extras_groupform(key, data, errors, context):
    # get current number of extras
    if data[key]:
        extra_number = 0
        for k in data.keys():
            if k[0] == 'extras':
                extra_number = max(extra_number, k[1] + 1)
        # add a new extra
        data[('extras', extra_number, 'key')] = key[0]
        if not context.get('extras_as_string'):
            data[('extras', extra_number, 'value')] = json.dumps(data[key])
        else:
            data[('extras', extra_number, 'value')] = data[key]

def convert_from_extras_groupform(key, data, errors, context):
    for k in data.keys():
        if (k[0] == 'extras' and
            k[-1] == 'key' and
            data[k] == key[-1]):
            # add to top level
            data[key] = data[('extras', k[1], 'value')]
