#!/bin/bash
./add_column_sqlite.sh $1 antenna
./add_column_sqlite.sh $1 rospecid
./add_column_sqlite.sh $1 channelindex
./add_column_sqlite.sh $1 tagseencount
./add_column_sqlite.sh $1 accessspecid
./add_column_sqlite.sh $1 inventoryparameterspecid
./add_column_sqlite.sh $1 lastseentimestamp
