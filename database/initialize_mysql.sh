#!/bin/bash
# root password is bellyband or '' or other defined password i.e. S1mbaby

#echo "CREATE DATABASE IF NOT EXISTS database; CREATE USER IF NOT EXISTS dbuser; SET PASSWORD FOR dbuser = PASSWORD('abc123'); GRANT ALL ON *.* TO dbuser;" | mysql -u root -p
python3 initialize_mysql.py '' database 'dbuser@localhost' abc123 localhost
