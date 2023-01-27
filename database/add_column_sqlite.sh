#!/bin/bash
# $1 is database name (database.db), $2 is column (antenna)
echo "ALTER TABLE IOTD ADD COLUMN $2 TEXT;" | sqlite3 $1
