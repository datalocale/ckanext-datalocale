#!/bin/bash

#
# Must be executed on the ckan root !
# This script allows to extract new strings from datalocale extension. 
#


if [ -e "../bin/python" ] 
then
    var=`readlink -f ../bin/python`
    alias python='$var'
fi

if [ -e "../../bin/python" ] 
then
    var=`readlink -f ../../bin/python`
    alias python='$var'
fi

i18ck="ckan/i18n"
i18dl="ckanext/datalocale/i18n"

fr="fr/LC_MESSAGES"
es="es/LC_MESSAGES"
en="en/LC_MESSAGES"


cd ckanext-datalocale/

# Extraction of new strings 
python setup.py extract_messages -o ckanext/datalocale/i18n/ckanext-datalocale.po

# Update of the language files
python setup.py update_catalog -l fr -i $i18dl/ckanext-datalocale.po 
python setup.py update_catalog -l es -i $i18dl/ckanext-datalocale.po
python setup.py update_catalog -l en -i $i18dl/ckanext-datalocale.po

cd -

# Find the duplicated strings FR
msgcat --more-than=1 --use-first -o ckanext-datalocale/$i18dl/$fr/tmp-ckan-Unique.po $i18ck/$fr/ckan.po.ori  ckanext-datalocale/$i18dl/$fr/ckan.po
# Extract datalocale strings FR
msgcat --less-than=2 --use-first -o ckanext-datalocale/$i18dl/$fr/tmp-dlUnique.po ckanext-datalocale/$i18dl/$fr/ckan.po ckanext-datalocale/$i18dl/$fr/tmp-ckan-Unique.po

# Find the duplicated strings ES
msgcat --more-than=1 --use-first -o ckanext-datalocale/$i18dl/$es/tmp-ckan-Unique.po $i18ck/$es/ckan.po.ori  ckanext-datalocale/$i18dl/$es/ckan.po
# Extract datalocale strings ES
msgcat --less-than=2 --use-first -o ckanext-datalocale/$i18dl/$es/tmp-dlUnique.po ckanext-datalocale/$i18dl/$es/ckan.po ckanext-datalocale/$i18dl/$es/tmp-ckan-Unique.po

# Find the duplicated strings FR
msgcat --more-than=1 --use-first -o ckanext-datalocale/$i18dl/$en/tmp-ckan-Unique.po $i18ck/$en/ckan.po.ori  ckanext-datalocale/$i18dl/$en/ckan.po
# Extract datalocale strings FR
msgcat --less-than=2 --use-first -o ckanext-datalocale/$i18dl/$en/tmp-dlUnique.po ckanext-datalocale/$i18dl/$en/ckan.po ckanext-datalocale/$i18dl/$en/tmp-ckan-Unique.po

mv ckanext-datalocale/$i18dl/$fr/tmp-dlUnique.po ckanext-datalocale/$i18dl/$fr/ckan.po
mv ckanext-datalocale/$i18dl/$en/tmp-dlUnique.po ckanext-datalocale/$i18dl/$en/ckan.po
mv ckanext-datalocale/$i18dl/$es/tmp-dlUnique.po ckanext-datalocale/$i18dl/$es/ckan.po

rm -f ckanext-datalocale/$i18dl/$fr/tmp-ckan-Unique.po
rm -f ckanext-datalocale/$i18dl/$es/tmp-ckan-Unique.po
rm -f ckanext-datalocale/$i18dl/$en/tmp-ckan-Unique.po
