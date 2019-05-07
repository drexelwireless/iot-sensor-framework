#!/bin/bash
mv database.db database.db.augment
./csv_unencrypted_to_sqlite.sh $1
./export_sqlitedb_csv.sh $1.db
mv database.db.augment database.db
