#!/bin/bash

# $1 is the CSV file with headers time and duration, with the time and duration of each outage that should be removed from the data.  Produces out.db0

python db_remove_gaps.py -p abc123 -g $1
