#!/bin/bash


patch -p1 < ckanext-datalocale/ckanext/datalocale/install_scripts/get.patch
patch -p1 < ckanext-datalocale/ckanext/datalocale/install_scripts/group.patch
patch -p1 < ckanext-datalocale/ckanext/datalocale/install_scripts/i18n.patch
patch -p1 < ckanext-datalocale/ckanext/datalocale/install_scripts/spatial.patch
