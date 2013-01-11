#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Usage: "$0" file_path"
    exit
fi

if [ ! -f $1 ]
then
    echo "Error: cannot access "$1": No such file or directory"
    exit
fi

source ckan-api-credentials.sh

FILEPATH=$1

CKAN_RESOURCE_UPLOAD_LOGS="ckan-file-upload.log"

API_URL="api/"

DATE=`date '+%Y-%m-%dT%H%M%S'`

FILENAME=$(basename $FILEPATH)
KEY=$DATE"/"$FILENAME

# Asking for http credential to send resource file
curl -v $CKAN_URL$API_URL$ACTION_RESOURCE_UPLOAD_CREDENTIALS$KEY -H "Authorization:"$CKAN_API_KEY""

echo ""
echo ""
echo ""

echo "Sending ressource: " $CKAN_URL$ACTION_RESOURCE_UPLOAD$KEY
# Sending resource form to http interface (-!- Not on the API -!-)
echo "\n\n\n\n KEY:$KEY\n\n" >> $CKAN_RESOURCE_UPLOAD_LOGS
curl  -v --form file=@$FILEPATH --form key=$KEY  -H "Authorization:"$CKAN_API_KEY"" $CKAN_URL$ACTION_RESOURCE_UPLOAD

echo ""
echo ""
echo ""

echo "Ressource key:" $KEY

echo ""
echo ""
echo ""

echo "Check if ressource now exists:"

curl  -v  $CKAN_URL$API_URL$ACTION_RESOURCE_READ$KEY | python -mjson.tool

echo ""
echo ""
