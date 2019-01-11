#!/bin/bash

# $1 is the database i.e. database.csv
python csv_to_sqlite.py -b $1.db -c $1 -p abc123
