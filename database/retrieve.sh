#!/bin/bash

curl -k -H "Content-Type: application/json" -X POST -d '{ "data": { "db_password": "abc123"} }' https://localhost:5000/api/rssi > out_rssi.txt

curl -k -H "Content-Type: application/json" -X POST -d '{ "data": { "db_password": "abc123"} }' https://localhost:5000/api/rssi/100/150 > out_rssi_timed.txt

#curl -k -H "Content-Type: application/json" -X POST -d '{ "data": { "db_password": "abc123"} }' https://localhost:5000/api/rssi/stats/window > out_window.txt

#curl -k -H "Content-Type: application/json" -X POST -d '{ "data": { "db_password": "abc123"} }' https://localhost:5000/api/rssi/stats/window/64 > out_window64.txt

#curl -k -H "Content-Type: application/json" -X POST -d '{ "data": { "db_password": "abc123"} }' https://localhost:5000/api/rssi/stats/relativetime/100/150 > out_reltime.txt

#curl -k -H "Content-Type: application/json" -X POST -d '{ "data": { "db_password": "abc123"} }' https://localhost:5000/api/rssi/stats/seconds > out_seconds.txt

#curl -k -H "Content-Type: application/json" -X POST -d '{ "data": { "db_password": "abc123"} }' https://localhost:5000/api/rssi/stats/seconds/1 > out_seconds1.txt

#curl -k -H "Content-Type: application/json" -X POST -d '{ "data": { "db_password": "abc123"} }' https://localhost:5000/api/rssi/stats/windows/100/150/10 > out_windows.txt

#curl -k -H "Content-Type: application/json" -X POST -d '{ "data": { "db_password": "abc123"} }' https://localhost:5000/api/rssi/stats/relativetimewindows/100/150/10 > out_timewindows.txt