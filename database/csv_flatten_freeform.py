import sys
import getopt
import csv
import json
import os
import math
import numpy as np
import time

def main():
    csvfilename = sys.argv[1]

    csvfile = open(csvfilename, 'rt')
    mycsv = csv.DictReader(csvfile)

    rows = []
    
    keys = {}
    
    i = 0
    for row in mycsv:
        if i == 0:
            for col in list(row.keys()):
                keys[col] = 1
        else:
            freeform = row['freeform']
            freeformdict = json.loads(freeform)
        
            if i == 1:
                for col in list(freeformdict.keys()):
                    keys[col] = 1
        
            for key in freeformdict:
                row[key] = freeformdict[key]
                
            rows.append(row)

        i = i + 1
            
    csvoutfile = open(csvfilename + '.flattened.csv', 'wt')
    mycsvout = csv.DictWriter(csvoutfile, fieldnames=list(keys.keys()),
                           quoting=csv.QUOTE_MINIMAL)

    mycsvout.writeheader()

    for row in rows:
        mycsvout.writerow(row)
    
    csvoutfile.close()
    os._exit(0)


if __name__ == "__main__":
    main()

# References:
#   http://kailaspatil.blogspot.com/2013/07/python-script-to-convert-json-file-into.html
