#!/bin/bash

cp $1 ./database.db
./retrieve_wholedb_json.sh 
mv out.csv $1.csv
