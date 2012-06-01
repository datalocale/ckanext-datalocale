from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
	name='ckanext-datalocale',
	version=version,
	description="Datalocale extension",
	long_description="""\
	""",
	classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
	keywords='',
	author='atos',
	author_email='oceane.ventura@atos.net',
	url='',
	license='',
	packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
	namespace_packages=['ckanext', 'ckanext.datalocale'],
	include_package_data=True,
	package_data = {'': ['*.xml', '*.html', '*.json']},
	zip_safe=False,
	install_requires=[
		# -*- Extra requirements: -*-
	],
	entry_points=\
	"""
        [ckan.plugins]
	# Add plugins here, eg
	# myplugin=ckanext.myextension:PluginClass
	datalocale_datasetform=ckanext.datalocale.forms:DatalocaleDatasetForm
	datalocale_serviceform=ckanext.datalocale.service_forms:DatalocaleServiceForm
	datalocale_api=ckanext.datalocale.api:DatalocaleAPI

	[paste.paster_command]
	datalocale = ckanext.datalocale.commands:DatalocaleCommand
	""",
)
