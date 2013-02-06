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


directory=$(dirname $0)

echo "Script directory :"$directory

i18ck="ckan/i18n"
i18dl="ckanext/datalocale/i18n"

fr="fr/LC_MESSAGES"
es="es/LC_MESSAGES"
en="en/LC_MESSAGES"


echo -n "Creating ckan english translation directory ... " 
# We create an English language directory if it not exists
mkdir -p $i18ck/$en
echo "[Done]"

echo -n "Copying some translations files ... "
# We import ckan core traductions (1.8)
cp ckanext-datalocale/$i18dl/$fr/ckan/ckan.po $i18ck/$fr/
cp ckanext-datalocale/$i18dl/$en/ckan/ckan.po $i18ck/$en/

cp $i18ck/$fr/ckan.po $i18ck/$fr/ckan.po.ori
cp $i18ck/$en/ckan.po $i18ck/$en/ckan.po.ori
cp $i18ck/$es/ckan.po $i18ck/$es/ckan.po.ori
echo "[Done]"

# We push the datalocale translations to make them usable by ckan core
./$directory/i18n-push-translations.sh

