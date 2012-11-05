#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Usage: "$0" resource_key"
    exit
fi

source ckan-api-credentials.sh

KEY=$1

API_URL="api/"
echo ""
echo ""
curl  -v  $CKAN_URL$API_URL$ACTION_RESOURCE_READ$KEY | python -mjson.tool
echo ""
echo ""