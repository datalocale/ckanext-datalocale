# -*-coding:utf-8 -*
import os
import sys
import re
import json
import urllib
import lxml.etree
import ckan
import ckan.model as model
import ckan.logic as logic
import ckan.lib.cli as cli
import requests
import forms
from xml.dom.minidom import parseString, parse

import logging
log = logging.getLogger()

VOCAB_FREQUENCES = u'dct:accrualPeriodicity'
VOCAB_THEMES = u'dcat:themeTaxonomy'
VOCAB_THEMES_CONCEPT = u'dcat:theme'
VOCAB_DATAQUALITY = u'dcat:dataQuality'
VOCAB_GRANULARITY = u'dcat:granularity'

class DatalocaleCommand(cli.CkanCommand):
    '''
    Commands:

        paster datalocale create-theme-vocab -c <config>
        paster datalocale create-frequence-vocab -c <config>
	paster datalocale create-dataQuality-vocab -c <config>
        paster datalocale create-granularity-vocab -c <config>
        paster datalocale delete-theme-vocab -c <config>
        paster datalocale delete-frequence-vocab -c <config>
	paster datalocale delete-dataQuality-vocab -c <config>
        paster datalocale delete-granularity-vocab -c <config>


	paster datalocale create-theme-vocab --config=/home/atos/pyenv/src/ckan/development.ini

    Where:
        <config> = path to your ckan config file

    The commands should be run from the ckanext-datalocale directory.
    '''
    summary = __doc__.split('\n')[0]

    def command(self):
        '''
        Parse command line arguments and call appropriate method.
        '''
        cmd = self.args[0]
        self._load_config()
	user = logic.get_action('get_site_user')(
            {'model': model, 'ignore_auth': True}, {}
        )
        self.user_name = user['name']
		
        if cmd == 'create-theme-vocab':
            self.create_theme_vocab()
	elif cmd == 'create-frequence-vocab':
	    self.create_frequence_vocab()
	elif cmd == 'create-dataQuality-vocab':
	    self.create_dataQuality_vocab()
	elif cmd == 'create-granularity-vocab':
	    self.create_granularity_vocab()
	elif cmd == 'delete-theme-vocab':
	    self.delete_theme_vocab()
	elif cmd == 'delete-frequence-vocab':
	    self.delete_frequence_vocab()
	elif cmd == 'delete-dataQuality-vocab':
	    self.delete_dataQuality_vocab()
	elif cmd == 'delete-granularity-vocab':
	    self.delete_granularity_vocab()
        else:
            log.error('Command "%s" not recognized' % (cmd,))
			
    def create_theme_vocab(self):
	log.info('theme_contexte_historique.xml')
        file_name = os.path.dirname(os.path.abspath(__file__)) + '/../../data/theme_contexte_historique.xml'
        self.create_vocab_from_file(VOCAB_THEMES, file_name)
	log.info('theme_actions.xml')
        file_name = os.path.dirname(os.path.abspath(__file__)) + '/../../data/theme_actions.xml'
        self.create_vocab_from_file(VOCAB_THEMES, file_name)
	log.info('theme_matieres.xml')
        file_name = os.path.dirname(os.path.abspath(__file__)) + '/../../data/theme_matieres.xml'
        self.create_vocab_from_file(VOCAB_THEMES, file_name)
	log.info('theme_typologie_documentaire.xml')
        file_name = os.path.dirname(os.path.abspath(__file__)) + '/../../data/theme_typologie_documentaire.xml'
        self.create_vocab_from_file(VOCAB_THEMES, file_name)

    def delete_theme_vocab(self):
	self._delete_special_vocab(VOCAB_THEMES)

    def create_frequence_vocab(self):
        tags = [u'journalier', u'hebdomadaire', u'mensuel', u'trimestriel' , u'semestriel', u'annuel']
        self.create_vocab_from_tags(VOCAB_FREQUENCES, tags)
	log.info('Vocabulary created')

    def delete_frequence_vocab(self):
	self._delete_vocab(VOCAB_FREQUENCES)

    def create_dataQuality_vocab(self):
        tags = [u'bonne', u'mauvaise']
        self.create_vocab_from_tags(VOCAB_DATAQUALITY, tags)
	log.info('Vocabulary created')

    def delete_dataQuality_vocab(self):
	self._delete_vocab(VOCAB_DATAQUALITY)

    def create_granularity_vocab(self):
        tags = [u'France', u'Département', u'longitude-latitude']
        self.create_vocab_from_tags(VOCAB_GRANULARITY, tags)
	log.info('Vocabulary created')

    def delete_granularity_vocab(self):
	self._delete_vocab(VOCAB_GRANULARITY)

    def create_vocab_from_tags(self, vocab_name, tags):
        context = {'model': model, 'session': model.Session,
                   'user': self.user_name}
		#creation du vocabulaire principal
        vocab = self._create_vocab(context, vocab_name)
        tag_schema = ckan.logic.schema.default_create_tag_schema()
	user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
	for tag in tags:
		context = {'model': model, 'session': model.Session, 'user': user['name'],
                           'schema': tag_schema}
		tag = {
			'name': unicode(tag),
			'vocabulary_id': vocab['id']
		}
		try:
		    logic.get_action('tag_create')(context, tag)
		    log.fatal('Tag "%s" created' % tag)
		except logic.ValidationError, ve:
		    ''' Ignore errors about the tag already belong to the vocab
		    	if it's a different error, reraise'''
		    if not 'already belongs to vocabulary' in str(ve.error_dict):
		        raise ve
		    log.fatal('Tag "%s" already belongs to vocab "%s"' %
		             (tag, vocab_name))	
	
    def create_vocab_from_file(self, vocab_name, file_name):
        context = {'model': model, 'session': model.Session,
                   'user': self.user_name}
		#creation du vocabulaire principal
        vocab = self._create_vocab(context, vocab_name)

        dom = parse(file_name)

        translations = []
        tag_schema = ckan.logic.schema.default_create_tag_schema()
        tag_schema['name'] = [unicode]

	user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})

	for conceptScheme in dom.getElementsByTagName('skos:ConceptScheme'):
		context = {'model': model, 'session': model.Session, 'user': user['name'],
                           'schema': tag_schema}
		thesaurus_uri = conceptScheme.getAttribute('ns0:about')
		print thesaurus_uri
		'''Add the THEME tag'''
		listTitle = conceptScheme.getElementsByTagName('dc:title')
		for title in listTitle:
			thesaurus_title =  title.childNodes[0].nodeValue
		print thesaurus_title
		tag = {
				'name': thesaurus_uri,
				'vocabulary_id': vocab['id']
			}
		try:
		    logic.get_action('tag_create')(context, tag)
		except logic.ValidationError, ve:
		    if not 'already belongs to vocabulary' in str(ve.error_dict):
		        raise ve
		    log.info('Tag "%s" already belongs to vocab "%s"' %
		             (thesaurus_uri, vocab_name))	
		'''Translation of the THEME tag'''
		translations.append({"term": thesaurus_uri,
					"term_translation": unicode(thesaurus_title),
					"lang_code": "fr"
					})		
		logic.get_action('term_translation_update_many')(
			context, {'data': translations}
		)
	'''Add the next vocabulary'''
	context = {'model': model, 'session': model.Session,
                   'user': self.user_name}
	vocab_theme = self._create_vocab(context, thesaurus_uri)
	
	translations = []
	for concept in dom.getElementsByTagName('skos:Concept'):
		context = {'model': model, 'session': model.Session, 'user': user['name'],
                           'schema': tag_schema}	
		concept_uri = concept.getAttribute('ns0:about')
		'''Add the THEME CONCEPT tag'''
		listTitle = concept.getElementsByTagName('skos:prefLabel')
		for title in listTitle:
			concept_title =  title.childNodes[0].nodeValue
			print concept_title
		tag = {
				'name': concept_uri,
				'vocabulary_id': vocab_theme['id']
			}
		try:
		    logic.get_action('tag_create')(context, tag)
		except logic.ValidationError, ve:
			if not 'already belongs to vocabulary' in str(ve.error_dict):
				raise ve
	    		log.info('Tag "%s" already belongs to vocab "%s"' % (concept_uri, vocab_theme['name']))	
			'''Translation of the THEME CONCEPT tag'''
	    	translations.append({"term": concept_uri,
				"term_translation": concept_title,
				"lang_code": "fr"
				})		
	logic.get_action('term_translation_update_many')(
		context, {'data': translations}
	)	

		
    def _create_vocab(self, context, vocab_name):
        try:
            log.info('Creating vocabulary "%s"' % vocab_name)
            vocab = logic.get_action('vocabulary_create')(
                context, {'name': vocab_name}
            )
        except logic.ValidationError, ve:
            if not 'name is already in use' in str(ve.error_dict):
                raise ve
            log.info('Vocabulary "%s" already exists' % vocab_name)
            vocab = logic.get_action('vocabulary_show')(
                context, {'id': vocab_name}
            )
        return vocab

    def _delete_vocab(self, vocab_name):
        log.info('Deleting vocabulary "%s"' % vocab_name)
        context = {'model': model, 'session': model.Session, 'user': self.user_name}
        vocab = logic.get_action('vocabulary_show')(context, {'id': vocab_name})
        for tag in vocab.get('tags'):
            logic.get_action('tag_delete')(context, {'id': tag['id']})
        logic.get_action('vocabulary_delete')(context, {'id': vocab['id']})

    def _delete_special_vocab(self, vocab_name):
        log.info('Deleting vocabulary "%s"' % vocab_name)
        context = {'model': model, 'session': model.Session, 'user': self.user_name}
        vocab = logic.get_action('vocabulary_show')(context, {'id': vocab_name})
        for tag in vocab.get('tags'):
	    sub_vocab = logic.get_action('vocabulary_show')(context, {'id': tag['name']})
	    for sub_tag in sub_vocab.get('tags'):
		logic.get_action('tag_delete')(context, {'id': sub_tag['id']})
	    logic.get_action('vocabulary_delete')(context, {'id': sub_vocab['id']})
            logic.get_action('tag_delete')(context, {'id': tag['id']})
        logic.get_action('vocabulary_delete')(context, {'id': vocab['id']})
