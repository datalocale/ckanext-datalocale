#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Usage: "$0" dataset_test_number"
    exit
fi

source ckan-api-credentials.sh


DATASET_TILE="Dataset test $1"
DATASET_URL_ID="dataset_test_$1" ## Must be unique

# DATALIFT SERVER CKAN PARAMS
GROUP_CKAN_ID="d4b3af9d-d989-4db3-8025-0f06ea6f87c1"
GROUP_URL_ID="atos"
GROUP_NAME="Atos"

SERVICE_CKAN_ID="e17b2efb-9f67-4d35-9ae9-3c176d93c14f"
SERVICE_URL_ID="service-a"
SERVICE_NAME="Service A"
# ! DATALIFT SERVER CKAN PARAMS


# ATOS DEVELOPMENT CKAN PARAMS
GROUP_CKAN_ID="b7b69275-ac16-4f44-9581-19e21120490b"
GROUP_URL_ID="atos"
GROUP_NAME="Atos"

SERVICE_CKAN_ID="644630ca-fd7d-46c4-9ad8-f0b26be1b74d"
SERVICE_URL_ID="service-a"
SERVICE_NAME="Service A"
# ! ATOS DEVELOPMENT CKAN PARAMS

DATE=`date '+%Y-%m-%dT%H%M%S'`

JSON='{
        "author": "", 
        "author_email": "", 
        "capacity": "public", 
        "ckan_author": "\"'$CKAN_AUTHOR_ID'\"", 
        "dataQuality": [], 
        "dc:source": "\"\"", 
        "dcat:granularity": "\"granularity_example\"", 
        "dct:accrualPeriodicity": "\"autre - merci de préciser\"", 
        "dct:accrualPeriodicity-other": "\"2 jours\"", 
        "dct:contributor": "\"'$CONTRIBUTOR_NAME'\"", 
        "dct:publisher": "\"'$GROUP_CKAN_ID'\"", 
	"dct:creator" : "\"'$SERVICE_CKAN_ID'\"",
        "dcterms:references": "\"example of dcterms:reference\"", 
        "geographic_granularity": "autre - merci de préciser", 
        "geographic_granularity-other": "\"Nationale\"", 
        "image_url": "\"\"", 
        "isopen": false, 
        "license_id": "", 
        "maintainer": "", 
        "maintainer_email": "", 
        "maj": "\"\"", 
        "name": "'$DATASET_URL_ID'", 
        "notes": "", 
        "state": "active", 
        "spatial-text": "\"GIRONDE\"", 
        "spatial-uri": "\"http://data.ign.fr/id/geofla/departement/33\"", 
        "themeTaxonomy":  "http://eurovoc.europa.eu/100156",
"theme_available" : "http://eurovoc.europa.eu/2556",
        "title": "'$DATASET_TILE'", 
        "type": "None", 
        "url": "", 
        "version": "",
	"tag_string": "mon tag, test",
	"resources" : [{"resource_type": "file.upload", "description": "Description of the ressource", "format": "csv", "hash": "md5:21cb13a5505f4dc831f9683b433cda8d", "size" : 274, "owner": "oceane", "name":"Name_of_the_resource", "last_modified": "", "url":"'$CKAN_URL'storage/f/2012-11-05T150255/Petit_Kiosques_ouverts_a_Paris.csv", "webstore_url":"'$CKAN_URL'storage/f/2012-11-05T150255/Petit_Kiosques_ouverts_a_Paris.csv"} ]
}'

# resources: you can get the informations from ./ckan-resource-read.sh resource_key

echo $JSON | python -mjson.tool

curl -v $CKAN_URL$API_URL$ACTION_PACKAGE_CREATE -H "Authorization:"$CKAN_API_KEY"" -d "$JSON" > /tmp/ckanPackageCreate.log 

cat /tmp/ckanPackageCreate.log | python -mjson.tool
