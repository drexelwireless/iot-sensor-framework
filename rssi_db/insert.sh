#!/bin/bash
# $1 = relative time (100), $2 = interrogator raw time (200), $3 = rssi (200), $4 = tag (abc123)
RSSI=$3
RELTIME=$1
INTEROTIME=$2
TAG=$4

for ((i=1;i<=100;i++));
do
	curl -k -H "Content-Type: application/json" -X PUT -d "{ \"data\": { \"db_password\": \"abc123\", \"rssi\": $((RSSI+i)), \"relative_time\": $((RELTIME+(i*500000))), \"interrogator_time\": \"$((INTEROTIME+i))\", \"epc96\": \"${TAG}\"} }" https://localhost:5000/api/rssi
done 

curl -k -H "Content-Type: application/json" -X PUT -d "[ { \"data\": { \"db_password\": \"abc123\", \"rssi\": $((RSSI+101)), \"relative_time\": $((RELTIME+(101*500000))), \"interrogator_time\": \"$((INTEROTIME+101))\", \"epc96\": \"${TAG}\"} }, { \"data\": { \"db_password\": \"abc123\", \"rssi\": $((RSSI+102)), \"relative_time\": $((RELTIME+(102*500000))), \"interrogator_time\": \"$((INTEROTIME+102))\", \"epc96\": \"${TAG}\"} } ]" https://localhost:5000/api/rssi
