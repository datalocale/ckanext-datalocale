import ckan.logic as logic
import ckan.lib.navl.dictization_functions as df
import ckan.logic.validators as val
import ckan.model as model

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
