#!/bin/bash

echo "DROP DATABASE IF EXISTS iotdatabase; DROP USER IF EXISTS 'dbuser@localhost';" | mysql -u root -p
