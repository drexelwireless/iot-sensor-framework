#!/bin/bash

echo "DROP DATABASE IF EXISTS rssidb; DROP USER IF EXISTS 'rssi@localhost';" | mysql -u root -p
