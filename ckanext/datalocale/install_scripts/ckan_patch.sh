#!/bin/bash


patch -p0 < ckanext-datalocale/ckanext/datalocale/install_scripts/get.patch
patch -p0 < ckanext-datalocale/ckanext/datalocale/install_scripts/group.patch
patch -p0 < ckanext-datalocale/ckanext/datalocale/install_scripts/i18n.patch
