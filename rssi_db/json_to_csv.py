import csv
import json
import sys

json_data = json.load(sys.stdin)
myjson = json_data['data']  # assumed to be a json array
keys = dict()

for k in myjson[0].keys():
    keys[k] = 1

mycsv = csv.DictWriter(sys.stdout, fieldnames=keys.keys(),
                       quoting=csv.QUOTE_MINIMAL)

mycsv.writeheader()
for row in myjson:
    mycsv.writerow(row)

# References:
#   http://kailaspatil.blogspot.com/2013/07/python-script-to-convert-json-file-into.html
