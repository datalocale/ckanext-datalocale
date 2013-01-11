#!/bin/bash
if [ $# -eq 0 ]; then
    echo "Usage: "$0" id"
    exit
fi

source ckan-api-credentials.sh

curl -v  $CKAN_URL$API_URL$ACTION_PACKAGE_SHOW -H "Authorization:"$CKAN_API_KEY"" -d '{"id":"'$1'"}' | python -mjson.tool

