#!/bin/bash

echo "DROP DATABASE IF EXISTS database; DROP USER IF EXISTS 'dbuser@localhost';" | mysql -u root -p
