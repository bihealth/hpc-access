#!/usr/bin/env bash

echo "***********************************************"
echo "Installing LDAP/AD dependencies"
echo "***********************************************"
sudo apt -y install libsasl2-dev
sudo apt -y install libldap2-dev
sudo apt -y install libssl-dev
