#!/bin/bash

# 
# Must be executed on the ckan root !
# This script push the content of the datalocale translations to be usable by ckan
#

if [ -e "../bin/python" ] 
then
    var=`readlink -f ../bin/python`
    alias python="$var"
    python_bin=$var
fi

if [ -e "../../bin/python" ] 
then
    var=`readlink -f ../../bin/python`
    alias python="$var"
    python_bin=$var
fi

i18ck="ckan/i18n"
i18dl="ckanext/datalocale/i18n"

fr="fr/LC_MESSAGES"
es="es/LC_MESSAGES"
en="en/LC_MESSAGES"


# We merge CKAN translations with DATALOCALE translations

echo -n "Merging file..."

msgcat --use-first -o $i18ck/$fr/ckan.po $i18ck/$fr/ckan.po.ori  ckanext-datalocale/$i18dl/$fr/ckan.po
msgcat --use-first -o $i18ck/$es/ckan.po $i18ck/$es/ckan.po.ori  ckanext-datalocale/$i18dl/$es/ckan.po
msgcat -o $i18ck/$en/ckan.po ckanext-datalocale/$i18dl/$en/ckan.po $i18ck/$en/ckan.po.ori

echo "[Done]"

echo -n "Message compilation ... "

$python_bin setup.py compile_catalog --use-fuzzy -l fr
$python_bin setup.py compile_catalog --use-fuzzy -l es
$python_bin setup.py compile_catalog --use-fuzzy -l en

echo "[Done]"