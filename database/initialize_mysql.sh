#!/bin/bash
# root password is bellyband or '' or other defined password i.e. S1mbaby

#echo "CREATE DATABASE IF NOT EXISTS rssidb; CREATE USER IF NOT EXISTS rssi; SET PASSWORD FOR rssi = PASSWORD('abc123'); GRANT ALL ON *.* TO rssi;" | mysql -u root -p
python3 initialize_mysql.py '' rssidb 'rssi@localhost' abc123 localhost
