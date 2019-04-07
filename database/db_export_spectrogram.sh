#!/bin/bash

# This method requires that the database is running
#curl -k -H "Content-Type: application/json" -X POST -d '{ "data": { "db_password": "abc123"} }' https://localhost:5000/api/rssi > out_rssi.txt
#cat out_rssi.txt | python json_to_csv.py >out_rssi.csv

python3 db_export_spectrogram.py -p abc123