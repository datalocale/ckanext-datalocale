
#!/usr/bin/python
try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from ckan import __version__, __description__, __long_description__, __license__
from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
	name='ckanext-datalocale',
	version=version,
	description="Datalocale extension",
	long_description="""\
	""",
	classifiers=[],
	keywords='',
	author='Atos',
	author_email='dorian.roncin@atos.net',
	url='',
	license='',
	packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
	namespace_packages=['ckanext', 'ckanext.datalocale'],
	include_package_data=True,
	package_data = {'ckanext/datalocale': ['*.xml', '*.html', '*.json', 'i18n/*/LC_MESSAGES/*.mo']},
	zip_safe=False,
	install_requires=[
	],
        message_extractors = {
        'ckanext/datalocale': [
            ('**.py', 'python', None),
            ('templates/importer/**', 'ignore', None),
            ('theme/templates/**.html', 'genshi', None),
            ('theme/templates/**.txt', 'genshi', {
                'template_class': 'genshi.template:TextTemplate'
            }),
            ('public/**', 'ignore', None),
        ],
        },
	entry_points=\
	"""
        [ckan.controllers]
	organization_datalocale=ckanext.datalocale.organization_controllers:DatalocaleOrganizationController
	diffuseur_datalocale=ckanext.datalocale.organization_controllers:DatalocaleOrganizationController
        service_datalocale=ckanext.datalocale.service_controllers:DatalocaleServiceController
	dataset_datalocale=ckanext.datalocale.dataset_controllers:DatalocaleDatasetController
	storage_datalocale=ckanext.datalocale.storage_controllers:DatalocaleStorageController
	
        [ckan.plugins]
      	datalocale_datasetform=ckanext.datalocale.forms_dataset:DatalocaleDatasetForm
	datalocale_serviceform=ckanext.datalocale.forms_service:DatalocaleServiceForm
	datalocale_organizationform=ckanext.datalocale.forms_organization:DatalocaleOrganizationForm
	datalocale_api=ckanext.datalocale.api:DatalocaleAPI

	[paste.paster_command]
	datalocale = ckanext.datalocale.commands:DatalocaleCommand
	
	""",
)
