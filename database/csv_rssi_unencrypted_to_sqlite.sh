#!/bin/bash

# for original non-freeform csv files
# $1 is the database i.e. database.csv
python3 csv_rssi_unencrypted_to_sqlite.py -b $1.db -c $1 -p abc123
