#!/bin/bash


CKAN_URL="http://localhost:5000"

API_URL="/api/storage/auth/form/tmp"

CKAN_API_KEY="2053b78f-7d13-4fee-8163-db18758c460c"

curl -v $CKAN_URL$API_URL -H "Authorization:"$CKAN_API_KEY"" 
