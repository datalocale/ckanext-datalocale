# -*-coding:utf-8 -*
# vim: set fileencoding=utf-8 :
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
from xml.dom.minidom import parse
import lxml.etree as xml
import gc
import ckanclient

import logging
log = logging.getLogger()

VOCAB_FREQUENCY = u'dct:accrualPeriodicity'
VOCAB_THEMES = u'dcat:themeTaxonomy'
VOCAB_THEMES_CONCEPT = u'dcat:theme'
VOCAB_DATAQUALITY = u'dcat:dataQuality'
VOCAB_GEOGRAPHIC_GRANULARITY = u'geographic_granularity'
VOCAB_TEMPORAL_GRANULARITY = u'dct:temporal'
VOCAB_REFERENCES = u'dcterms:references'
tags_frequency = [u'jamais', u'irrégulier', u'annuelle', u'semestrielle' , u'trimestrielle', u'mensuelle', u'quotidienne', u'autre - merci de préciser']
tags_geographic_granularity = [u'régional', u'départemental', u'etablissement public', u'commune', u'association', u'autre - merci de préciser']
tags_temporal_granularity = [u'année', u'trimestre', u'mois', u'semaine', u'jour', u'heure', u'point', u'autre - merci de préciser']
tags_dataQuality = [u'exhaustive', u'à améliorer', u'à enrichir', u'référence', u'échantillon']

namespace_rdf = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
namespace_skos = 'http://www.w3.org/2004/02/skos/core#' 
namespace_xml = 'http://www.w3.org/XML/1998/namespace'
namespace_eu = 'http://eurovoc.europa.eu/schema#'
namespace_dc = 'http://purl.org/dc/elements/1.1/'
            
class DatalocaleCommand(cli.CkanCommand):
    '''
    Commands:

	paster datalocale create-all-vocab -c <config>
	paster datalocale delete-all-vocab -c <config>
	
	paster datalocale create-theme-vocab -c <config>
	paster datalocale create-eurovoc-vocab -c <config>
	paster datalocale create-frequency-vocab -c <config>
	paster datalocale create-dataQuality-vocab -c <config>
	paster datalocale create-geographic-granularity-vocab -c <config>
	paster datalocale create-temporal-vocab -c <config>
	paster datalocale delete-theme-vocab -c <config>
	paster datalocale delete-eurovoc-vocab -c <config>
	paster datalocale delete-frequency-vocab -c <config>
	paster datalocale delete-dataQuality-vocab -c <config>
	paster datalocale delete-geographic-granularity-vocab -c <config>
	paster datalocale delete-temporal-vocab -c <config>

    paster datalocale dump-rdf <path> -c <config>
    paster datalocale dump-json <path> -c <config>
    paster datalocale dump-csv <path> -c <config>
    paster datalocale dump -c <config>
    
    Example:
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
        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        self.user_name = user['name']
        if cmd == 'create-theme-vocab':
            self.create_theme_vocab()
        elif cmd == 'create-eurovoc-vocab':
            self.create_eurovoc_vocab()
        elif cmd == 'create-frequency-vocab':
            self.create_frequency_vocab()
        elif cmd == 'create-dataQuality-vocab':
            self.create_dataQuality_vocab()
        elif cmd == 'create-geographic-granularity-vocab':
            self.create_geographic_granularity_vocab()
        elif cmd == 'create-temporal-vocab':
            self.create_temporal_vocab()
        elif cmd == 'create-all-vocab':
            self.create_all_vocab()
        elif cmd == 'delete-theme-vocab':
            self.delete_theme_vocab()
        elif cmd == 'delete-eurovoc-vocab':
            self.delete_eurovoc_vocab()
        elif cmd == 'delete-frequency-vocab':
            self.delete_frequency_vocab()
        elif cmd == 'delete-dataQuality-vocab':
            self.delete_dataQuality_vocab()
        elif cmd == 'delete-geographic-granularity-vocab':
            self.delete_geographic_granularity_vocab()
        elif cmd == 'delete-temporal-vocab':
            self.delete_temporal_vocab()
        elif cmd == 'delete-all-vocab':
            self.delete_all_vocab()
        elif cmd == 'dump-rdf':
            if len(self.args) == 2:
                self.dump_rdf(self.args[1])
        elif cmd == 'dump-json':
            if len(self.args) == 2:
                self.dump_json(self.args[1])
        elif cmd == 'dump-csv':
            if len(self.args) == 2:
                self.dump_csv(self.args[1])
        elif cmd == 'dump':
            self.dump()
        elif cmd == 'import-csv':
            if len(self.args) == 7:
                self.import_csv(self.args[1], self.args[2], self.args[3], self.args[4], self.args[5], self.args[6])
            if len(self.args) == 5:
                self.import_csv(self.args[1], self.args[2], self.args[3], self.args[4]) 
	else:
            log.error('Command "%s" not recognized' % (cmd,))
            
    def create_all_vocab(self):
        self.create_frequency_vocab()
        self.create_dataQuality_vocab()
        self.create_geographic_granularity_vocab()
        self.create_temporal_vocab()
        self.create_theme_vocab()
    
    def delete_all_vocab(self):
        self.delete_frequency_vocab()
        self.delete_dataQuality_vocab()
        self.delete_geographic_granularity_vocab()
        self.delete_temporal_vocab()
        self.delete_theme_vocab()
    
    def create_theme_vocab(self):
        log.info('Creation in progress...')
        file_name = os.path.dirname(os.path.abspath(__file__)) + '/../../data/theme_eurovoc.xml'
        self.create_vocab_from_file(VOCAB_THEMES, file_name)
        log.info('Vocabulary created : theme')
    
    def delete_theme_vocab(self):
        self._delete_special_vocab(VOCAB_THEMES)
        
    def delete_eurovoc_vocab(self):
        self._delete_special_vocab(VOCAB_THEMES)
    
    def create_frequency_vocab(self):
        self.create_vocab_from_tags(VOCAB_FREQUENCY, tags_frequency)
    
    def delete_frequency_vocab(self):
        self._delete_vocab(VOCAB_FREQUENCY)
    
    def create_dataQuality_vocab(self):
        self.create_vocab_from_tags(VOCAB_DATAQUALITY, tags_dataQuality)
    
    def delete_dataQuality_vocab(self):
        self._delete_vocab(VOCAB_DATAQUALITY)
    
    def create_geographic_granularity_vocab(self):
        self.create_vocab_from_tags(VOCAB_GEOGRAPHIC_GRANULARITY, tags_geographic_granularity)
    
    def delete_geographic_granularity_vocab(self):
        self._delete_vocab(VOCAB_GEOGRAPHIC_GRANULARITY)
         
    def create_temporal_vocab(self):
        self.create_vocab_from_tags(VOCAB_TEMPORAL_GRANULARITY, tags_temporal_granularity)
    
    def delete_temporal_vocab(self):
        self._delete_vocab(VOCAB_TEMPORAL_GRANULARITY)
    
    def create_vocab_from_tags(self, vocab_name, tags):
        context = {'model': model, 'session': model.Session,
                   'user': self.user_name}
        #creation du vocabulaire principal
        vocab = self._create_vocab(context, vocab_name)
        tag_schema = logic.schema.default_create_tag_schema()
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
                log.info('Tag "%s" created' % tag)
            except logic.ValidationError, ve:
                ''' Ignore errors about the tag already belong to the vocab
                if it's a different error, reraise'''
                if not 'already belongs to vocabulary' in str(ve.error_dict):
                    raise ve
                log.fatal('Tag "%s" already belongs to vocab "%s"' % (tag, vocab_name))	
        log.info('Vocabulary created')
    
    def create_vocab_from_file(self, vocab_name, filename):
        ''' Initialisation '''
        tag_schema = logic.schema.default_create_tag_schema()
        tag_schema['name'] = [unicode]
        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context_tag = {'model': model, 'session': model.Session, 'user': user['name'], 'schema': tag_schema}
        context_model = {'model': model, 'session': model.Session,'user': self.user_name}
        
        path_dctitle = '{{{dc}}}title'.format(dc=namespace_dc, xml=namespace_xml)
        path_preflabel = '{{{skos}}}prefLabel[@{{{xml}}}lang="fr"]'.format(skos=namespace_skos, xml=namespace_xml)
        path_inScheme = '{{{skos}}}inScheme'.format(skos=namespace_skos, xml=namespace_xml)
        
        vocab = self._create_vocab(context_model, vocab_name)
        filename_parse = xml.parse(filename)
        xml_skosConceptScheme = xml.iterparse(filename, events=('end',), tag='{{{skos}}}ConceptScheme'.format(skos=namespace_skos))
        xml_skosConceptScheme_type = filename_parse.xpath('/rdf:RDF/rdf:Description/rdf:type[@rdf:resource="'+namespace_skos+'ConceptScheme"]',
                                                               namespaces={'rdf': namespace_rdf})
        xml_skosConcept = xml.iterparse(filename, events=('end',), tag='{{{skos}}}Concept'.format(skos=namespace_skos))
        xml_skosConcept_type = filename_parse.xpath('/rdf:RDF/rdf:Description/rdf:type[@rdf:resource="'+namespace_skos+'Concept"]',
                                                               namespaces={'rdf': namespace_rdf})
        listConcept = {}
        listConceptScheme = {}
        listInScheme = {} #Parent : Fils
        
        print('Searching for "Concept"...')
        #Get Concept list. Type <skos:Concept>
        for event, elem in xml_skosConcept:
            Concept_uri = elem.get("{{{rdf}}}about".format(rdf=namespace_rdf))
            Concept_title = elem.find(path_preflabel).text
            inScheme_uri = elem.find(path_inScheme).get("{{{rdf}}}resource".format(rdf=namespace_rdf))
            listConcept[Concept_uri] = Concept_title
            if inScheme_uri in listInScheme:
                listInScheme[inScheme_uri].append(Concept_uri)
            else:
                listInScheme[inScheme_uri] = [Concept_uri]
            #print(Concept_title, Concept_uri, inScheme_uri)
        del(xml_skosConcept)
        
        print('Searching for "Concept"...')
        #Get Concept list.Type <rdf:Description><type=skos:Concept>
        for elem in xml_skosConcept_type:
            parent = elem.getparent()
            Concept_uri = parent.get("{{{rdf}}}about".format(rdf=namespace_rdf))
            Concept_title = parent.find(path_preflabel).text
            inScheme_uri = parent.find(path_inScheme).get("{{{rdf}}}resource".format(rdf=namespace_rdf))
            listConcept[Concept_uri] = Concept_title
            if inScheme_uri in listInScheme:
                listInScheme[inScheme_uri].append(Concept_uri)
            else:
                listInScheme[inScheme_uri] = [Concept_uri]
            #print(Concept_uri, Concept_title, inScheme_uri)
        del(xml_skosConcept_type) 
        
        print('Searching for "ConceptScheme"...')
        #Get ConceptScheme. Type <skos:ConceptScheme>
        for event, elem in xml_skosConceptScheme:
            ConceptScheme_uri = elem.get("{{{rdf}}}about".format(rdf=namespace_rdf))
            ConceptScheme_title = elem.find(path_dctitle).text
            listConceptScheme[ConceptScheme_uri] = ConceptScheme_title
            #print(ConceptScheme_title, ConceptScheme_uri)
        del(xml_skosConceptScheme)
        
        print('Searching for "ConceptScheme"...')
        #Get ConceptScheme. Type <rdf:Description><type=skos:ConceptScheme>
        for elem in xml_skosConceptScheme_type:
            parent = elem.getparent()
            ConceptScheme_uri = parent.get("{{{rdf}}}about".format(rdf=namespace_rdf))
            ConceptScheme_title = parent.find(path_dctitle).text
            listConceptScheme[ConceptScheme_uri] = ConceptScheme_title
            #print(ConceptScheme_uri, ConceptScheme_title)
        del(xml_skosConceptScheme_type)
        
        print('Matching "ConceptScheme" to "Concept"...')
        for ConceptScheme_uri in listConceptScheme :
            ConceptScheme_title = listConceptScheme[ConceptScheme_uri]
            print("\t Saving :" + ConceptScheme_title)
            self._create_tag(context_tag, vocab, ConceptScheme_uri, ConceptScheme_title)
            vocab_ConceptScheme = self._create_vocab(context_model, ConceptScheme_uri)
            for Concept_uri in listInScheme.get(ConceptScheme_uri):
                Concept_title = listConcept.get(Concept_uri)
                self._create_tag(context_tag, vocab_ConceptScheme, Concept_uri, Concept_title)
            del(listInScheme[ConceptScheme_uri])
            
    
    def _create_vocab(self, context_model, vocab_name):
            try:
                print('Creating vocabulary "%s"' % vocab_name)
                vocab = logic.get_action('vocabulary_create')(
                    context_model, {'name': vocab_name}
                )
            except logic.ValidationError, ve:
                if not 'name is already in use' in str(ve.error_dict):
                    raise ve
                print('Vocabulary "%s" already exists' % vocab_name)
                vocab = logic.get_action('vocabulary_show')(
                    context_model, {'id': vocab_name}
                )
            return vocab   
             
    def _create_tag(self, context_tag, vocab, uri, label):
        try:
            tag = {'name': uri.encode('utf-8'),'vocabulary_id': vocab['id'].encode('utf-8')}
            logic.get_action('tag_create')(context_tag, tag)
            translations = []
            translations.append({"term": uri,
                    "term_translation": label,
                    "lang_code": "fr"})  
            logic.get_action('term_translation_update_many')(context_tag, {'data': translations})   
            del(translations)   
        except logic.ValidationError, ve:
            if not 'already belongs to vocabulary' in str(ve.error_dict):
                raise ve
    
    def _delete_vocab(self, vocab_name):
        log.info('Deleting vocabulary "%s"' % vocab_name)
        context = {'model': model, 'session': model.Session, 'user': self.user_name}
        try:
            vocab = logic.get_action('vocabulary_show')(context, {'id': vocab_name})
            for tag in vocab.get('tags'):
                logic.get_action('tag_delete')(context, {'id': tag['id']})
                logic.get_action('vocabulary_delete')(context, {'id': vocab['id']})
        except logic.NotFound:
            log.fatal('Vocabulary not found %s' % vocab_name)
            pass
    
    def _delete_special_vocab(self, vocab_name):
        log.fatal('Deleting vocabulary "%s"' % vocab_name)
        context = {'model': model, 'session': model.Session, 'user': self.user_name}
        try:
            vocab = logic.get_action('vocabulary_show')(context, {'id': vocab_name})
            for tag in vocab.get('tags'):
                log.fatal('Vocab available: %s' % str(tag['name']))
                try:
                    sub_vocab = logic.get_action('vocabulary_show')(context, {'id': tag['name']})
                    if sub_vocab:
                        for sub_tag in sub_vocab.get('tags'):
                            logic.get_action('tag_delete')(context, {'id': sub_tag['id']})
                        logic.get_action('vocabulary_delete')(context, {'id': sub_vocab['id']})
                except logic.NotFound:
                    log.fatal('Sub vocab not found for vocab %s' % tag["name"])
                logic.get_action('tag_delete')(context, {'id': tag['id']})
            logic.get_action('vocabulary_delete')(context, {'id': vocab['id']})
        except logic.NotFound:
            log.fatal('Vocabulary not found %s' % vocab_name)
            pass

    def dump_rdf(self, path):
        import urlparse
        import urllib2
        import pylons.config as config
        import ckan.lib.helpers as h
        import re
        first = True
        fetch_url = config['ckan.site_url']
        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        context = {'model': model, 'session': model.Session, 'user': user['name']}
        dataset_names = logic.get_action('datalocale_package_list')(context, {})
        rdf = ""
        dataset_nb = len(dataset_names)
        i = 0
        start_with = 'xmlns:dcterms="http://purl.org/dc/terms">'
        end_with = '</rdf:RDF>'
        for dataset_name in dataset_names:
            dd = logic.get_action('package_show')(context, {'id':dataset_name })
            if not dd['state'] == 'active':
                continue

            url = h.url_for( controller='package',action='read',
                                                  id=dd['name'])

            url = urlparse.urljoin(fetch_url, url[1:]) + '.rdf'
            try:
                rdf_filecontent = urllib2.urlopen(url).read()
                if first:
                    rdf += rdf_filecontent[:rdf_filecontent.index(end_with)]
                else:
                    rdf_filecontent = rdf_filecontent[rdf_filecontent.index(start_with)+len(start_with):rdf_filecontent.index(end_with)]
                    rdf += rdf_filecontent
                if i+1 >= dataset_nb:
                    rdf += end_with

            except IOError, ioe:
                sys.stderr.write( str(ioe) + "\n" )
            first = False
            i += 1
        f = open(path, 'w')
        f.write(rdf)
        f.close()
                        
    def _get_package_public(self):
        from sqlalchemy.sql import and_, or_
        query = model.Session.query(model.Package).\
        join(model.PackageRole,model.PackageRole.package_id == model.Package.id).\
        join(model.UserObjectRole, model.UserObjectRole.id == model.PackageRole.user_object_role_id).\
        join(model.User,model.User.id == model.UserObjectRole.user_id).\
        filter(model.Package.state == 'active').\
        filter(model.User.name == 'visitor').\
        outerjoin(model.Member, model.Member.table_id == model.Package.id).\
        filter(or_(model.Member.capacity=='public', model.Member.capacity ==None ))
        return query
    
    def dump_json(self, path):
        query = self._get_package_public()
        from time import gmtime, strftime
        dump_file = open(path, 'w')
        pkgs = []
        for pkg in query:
            pkg_dict = pkg.as_dict()
            pkgs.append(pkg_dict)
        json_content = []
        timestamp = {"last update" : strftime("%d-%m-%Y %H:%M:%S", gmtime()) }
        json_content.append(timestamp)
        json_content.append({"results": pkgs})
        json.dump(json_content, dump_file, indent=4)

    def dump_csv(self, path):
        import csv
        from ckan.lib.dumper import CsvWriter
        import codecs
        query = self._get_package_public()
        dump_file = open(path, 'w')
        dump_file.write(codecs.BOM_UTF8)
        row_dicts = []
        for pkg in query:
            pkg_dict = pkg.as_dict()
            # flatten dict
            for name, value in pkg_dict.items()[:]:
                if isinstance(value, (list, tuple)):
                    if value and isinstance(value[0], dict) and name == 'resources':
                        for i, res in enumerate(value):
                            prefix = 'resource-%i' % i
                            pkg_dict[prefix + '-url'] = res['url']
                            pkg_dict[prefix + '-format'] = res['format']
                            pkg_dict[prefix + '-description'] = res['description']
                    elif value and isinstance(value[0], dict) and name == 'license_id':
                            pkg_dict[name] = ' '.join(value)
                    else:
                        pkg_dict[name] = ' '.join(value)
                if isinstance(value, dict):
                    for name_, value_ in value.items():
                        pkg_dict[name_] = value_
                    del pkg_dict[name]
            row_dicts.append(pkg_dict)
        writer = CsvWriter(row_dicts)
        writer_csv = csv.writer(dump_file, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        col_titles = []
        for cols in writer._col_titles:
            col_titles.append(cols.encode('utf-8'))
        writer_csv.writerow(col_titles)
        for row in writer._rows:
            writer_csv.writerow(row)	
        
    def dump(self, path = None):
        folder = './public/dump/'
        if not os.path.isdir( folder ):
            os.makedirs( folder )
        filename = folder + 'Datalocale'
        self.dump_csv(filename + '.csv')
        self.dump_json(filename + '.json')
        self.dump_rdf(filename + '.rdf')
         
    def import_csv(self, file_path, user, separator, data_line, publisher_name = None, creator_name = None):
        ''' Récupéreration l'utilisateur en cours'''
        ckan = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        ckan_user = model.User.get(user)
        publisher = model.Group.get(publisher_name)
        creator = model.Group.get(creator_name)
        '''Inisialisation du client API'''
        ckanc = ckanclient.CkanClient(base_location="http://localhost:5000/api",
                             api_key="2053b78f-7d13-4fee-8163-db18758c460c")
        ''' Récupéreration du chemin du fichier csv'''
        file = file_path
        with open(file, 'r') as f:
            csv.register_dialect("myDialect", MyDialect) 
            '''Paramétrage du format de sortie du CSV'''
            reader = csv.reader(open(file), delimiter=separator, dialect = "myDialect")
            '''Création de la table d'association du fichier CSV'''
            fields = self._csv_set_match()
            '''Parcours du fichier jusqu'à la première ligne de données'''
            i = 0
            while i < int(data_line) - 1:
                reader.next()
                i = i + 1
            '''Création du jeux de données à ajouter'''
            for row in reader:
                '''Ajout des valeurs par défaut à tous les jeux de données'''
                dataset_package = self._csv_setdefaults(ckan_user, publisher, creator)
                '''Ajout des valeurs récupérées dans le fichier'''
                self._csv_setdata(dataset_package, row, fields)
                '''Ajout des ressources du jeux de données'''
                if row[24] != "":
                    dataset_resource = self._csv_setresources(row)
                    dataset_package["resources"] = dataset_resource
                '''Enregistrement du jeux de données'''
                ckanc.package_register_post(dataset_package)
            
    def _csv_set_match(self):
        m_match = {
                      "dc:source": 1,
                       "name": 2,
                       "title": 3,
                       "dct:description": 4,
                       "dcat:theme": -1,
                       "inspire": -1,
                       "dcat:keywords": -1,
                       "license_id": 8,
                       "dct:issued": -1,
                       "dct:modified": -1,
                       "obj_maj": 11,
                       "dct:accrualPeriodicity": 12,
                       "dct:created": -1,
                       "dct:creator": -1,
                       "dct:publisher": -1,
                       "dct:contributor": 16,
                       "dct:spatial": -1,
                       "dct:temporal": -1,
                       "dct:language": -1,
                       "dct:format": -1,
                       "dcat:dataQuality": -1,
                       "dcat:granularity": 22,
                       "dterms:reference": 23,
                       "dcat:themeTaxomony": -1,
                  }
        return m_match
    
    def _csv_setdefaults(self, client, publisher, creator):
        if (publisher == None):
            publisher = ""
        else:
            publisher = publisher.id
        if (creator == None):
            creator = ""
        else:
            creator = creator.id
        dataset_package = {
                           "capacity": "public",
                           "ckan_author": "\"'%s'\"" % client, 
                           "dct:publisher": "\"%s\"" % publisher, 
                           "dct:creator" : "\"%s\"" % creator,
                           "geographic_granularity": "autre - merci de préciser", 
                           "geographic_granularity-other": "\"Nationale\"", 
                          }
        return dataset_package
    
    def _csv_setdata(self, dataset_package, row, fields):
        for value in fields:
            if fields.get(value) != -1:
                  if value == "name":
                      dataset_package[value] = unicode(row[fields.get(value) - 1] + "-a", "utf-8")
                      dataset_package[value] = dataset_package[value].lower()
                  elif value == "title":
                      dataset_package[value] = unicode(row[fields.get(value) - 1], "utf-8")
                  elif value == "dc:source":
                      dataset_package[value] = "\"%s\"" % row[fields.get(value) - 1]
                  elif value == "dcat:granularity":
                      dataset_package[value] = "\"%s\"" % unicode(row[fields.get(value) - 1], "utf-8")
                  elif value == "dct:modified":
                      dataset_package["obj_maj"] = "\"%s\"" % row[fields.get(value) - 1]
                  elif value == "dct:accrualPeriodicity":
                      dataset_package[value] = "\"%s\"" % row[fields.get(value) - 1]
                      dataset_package[value] = dataset_package[value].lower()
                  elif value == "dct:description":
                      dataset_package["notes"] = unicode(row[fields.get(value) - 1], "utf-8")
                  elif value == "dct:contributor":
                      dataset_package[value] = "\"%s\"" % unicode(row[fields.get(value) - 1], "utf-8")
                  elif value == "dterms:reference":
                      dataset_package["dterms:reference"] = "\"%s\"" % row[fields.get(value) - 1]
                  elif value == "license_id":
                      dataset_package[value] = row[fields.get(value) - 1]
#                  elif value == "dct:temporal":
#                      temporal = row[fields.get(value) - 1]
#                      dates = {}
#                      type1 = re.compile('\d{4}\sà\s\d{4}')
#                      type2 = re.compile('\d{4}\s-\s\d{4}')
#                      if type1.match(temporal) != None:
#                          dates = self._format_dataset_date(type1.match(temporal).group())
#                          dataset_package["temporal_coverage-from"] = "\"%s\"" % unicode(dates["beg"], "utf-8")
#                          dataset_package["temporal_coverage-to"] = "\"%s\"" % unicode(dates["end"], "utf-8")
#                      elif type2.match(temporal) != None:
#                          dates = self._format_dataset_date(type2.match(temporal).group())
#                          dataset_package["temporal_coverage-from"] = "\'%s\'" % dates["beg"]
#                          dataset_package["temporal_coverage-to"] = "\'%s\'" % dates["end"]
    
#    def _format_dataset_date(self, raw):
#        m_dates = {}
#        str1 = raw
#        m_dates["beg"] = "01/01/" + str1[0:4]
#        str2 = raw
#        m_dates["end"] = "01/01/" + str2[-4:len(str2)]
#        return m_dates
    
    def _csv_setresources(self, row):
	resource = [{
			     "url": unicode(row[27], "utf-8"),
                 "resource_type": row[24],
                 "format": row[25],
                 "name": row[26]
		       }]
        return resource
    
import csv
class MyDialect(csv.excel): 
        lineterminator = "\n" 


        
