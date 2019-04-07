#!/bin/bash

# $1 is the EPC that should be removed.  Produces out.db0

python3 db_remove_epc.py -p abc123 -g $1
