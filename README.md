[![v1.0 Release DOI, 5/5/2020](https://zenodo.org/badge/DOI/10.5281/zenodo.3786932.svg)](https://doi.org/10.5281/zenodo.3786932)

# IoT Data Collection and Storage Software

This software suite contains scripts to collect and store IoT sensor data, such as RFID tag information using an Impinj Speedway RFID reader.

*Note: These instructions assume that the web server and interrogation 
software will be run on the same machine (IP addresses in all shell scripts
have been set to `localhost`).  The host, port, keys, and other parameters can be set when running the scripts in the instructions.  

## Installation Videos
Installation Tutorial Videos can be found [here](https://www.youtube.com/playlist?list=PLM-MEGowMWmQa1SF-a9Xhoz0yrDuEZ1B9)

## On Windows - Install VcXsrv or Another X Window Server
You can download [VcXsrv here](https://sourceforge.net/projects/vcxsrv/).

To forward X connections to your local computer, run `XLaunch` and export the following variable:

`export DISPLAY=localhost:0.0`

You might add this to your `.bashrc` file so that the variable is automatically set at login:

`echo "export DISPLAY=localhost:0.0" >> ~/.bashrc`

## Requirements
The following software packages need to be installed before running 
data collection. You will have to use the same install method (such as
`pip install` or `easy_install`) listed here. Also, alternatives to using
`sudo` for `pip install` are  `sudo -H pip install <package-name>` or
`pip install --user <package-name>`.

See the Dockerfile in each subdirectory for deployment instructions; these can be executed manually for a local installation, or containerized using Docker.

The deployment script deploy.sh will also handle the installation steps locally.

This package assumes an installation of python3 and pip3.

## generate a web server key
```
openssl req -newkey rsa:2048 -nodes -keyout key.key -x509 -days 365 -out key.crt
```

### System Architecture
#### Interrogator Drivers
The `Interrogator` is implemented by a client driver *i.e.*, the 
`ImpinjR420` class), which implements the `start()` method.  Typically, this 
method creates two threads: a `Producer` thread which collects interrogated data from 
the device and appends it to a queue, and a `Consumer` thread, 
which awaits data on the 
queue and transmits it to the server via a RESTful network call at the 
specified "dispatch" interval.  This is known as the Producer-Consumer 
pattern; this approach separates the 
high-latency network or disk operations from the interrogation functionality, so that the 
interrogator may continue to produce data while collected records are stored.

Once the queue and Producer/Consumer threads are initialized, the driver connects to the
device or instantiates a library 
to handle the physical-layer communications if one 
is available.  As tags are received, they are inserted into the queue.  No additional 
processing takes place, so that latency between interrogations is minimized.  The consumer
thread iteratively polls the queue for new data, collects them into an array, and initiates
a RESTful web service POST call to the framework database server to store them.  The interrogation client can be invoked as follows: 

`python3 client.py -i <interrogator IP address> -p <data encryption/decryption password> -g r420 -a <antenna number(s), separated by comma> -l <dispatch sleep time in seconds or fractions of a second>}`

where `r420` specifies the device driver to instnatiate (*i.e.*, `r420` for an Impinj R420, `impinj` for an Impinj R1000, or `xarray` for an Impinj XArray R680; these options are not limited to Impinj devices nor to RFID interrogators).

#### Database Layer
The `Server` class instantiates the database driver and the web server endpoints that 
receive data from the interrogator and pass it to the database interface.  

The database server is invoked via 
`python3 server.py -e <dispatch sleep time in seconds or fractions of a second>}`  

A test SSL certificate and encryption key are provided but can and should be 
generated for each deployment.  By default, the database uses a Sqlite database called 
`database.db` (The database filename can be specified by passing the 
`-b <database filename>` parameter to `server.py`.
  
If this file does not exist, it will be created; 
otherwise, it is appended to.  Sqlite is useful because the databases are portable; we have saved 
several years of data collected in a repository for future experimentation and repeated analysis.  
However, because it is a disk-based database, it is not suitable for real-time data collection.  
Therefore, if an interrogator is to be invoked, it is recommended to use another 
database engine such as MySQL.  The `-m` parameter can be passed to `server.py` 
to specify a MySQL database engine (with additional parameters 
`-s <mysql user name> -w <mysql password> -b <mysql server IP>` to configure it).  
Similarly, the `-o` parameter can be passed to specify a MongoDB database (with 
additional parameter `-b <database directory>` to configure it).

The server is invoked first, optionally followed by an interrogator driver to generate data,
and also optionally followed by a processing module to visualize or process the data.  
If an interrogator driver is not 
invoked, an existing database can be opened by the server and processed as if it was 
in real-time by a visualizer or processing node.

#### RESTful Communications Layer
The webserver is invoked automatically by the server, and is a Python Flask RESTful service 
provider.  It provides web service endpoints to both retrieve and store data, as summarized
in the Table below.  Parameters and body responses are provided as JSON 
objects, with an outer object called \texttt{data} that encapsulates either an object or 
an array of objects.  A data record takes the form shown in the Listing below.

``
"data": [
    {
        "relative_timestamp": 500,
        "absolute_time": 1/1/2016 23:59:59.12345,
        "interrogator_timestamp": 10500,
        "id": 0,
        "freeform": '{
            "rssi": -38,
            "doppler": 0,
            "phase": 0,
            "epc96": "2015abc",
            "antenna": 1,
            "channelIndex": 9
        }'
    },
    ...
]
``

The `interrogator_timestamp` is a numeric timestamp in microseconds or milliseconds, 
which is converted by the interrogator driver to an `interrogator_timestamp` prior 
to sending to the webserver.  This is done by subtracting the first observed 
`interrogator_timestamp` from the current one to obtain a time value that starts
with 0.  An `absolute\_timestamp` is provided which is the datetime that the 
packet was received by the interrogator, or by the interrogator driver if the field 
is omitted by the device.  An `id` serial number is provided, and, finally, a 
`freeform` field.  

This `freeform` field is a string that is typically populated with a JSON body.  
However, no restriction is placed on its format, so that other data types are supported (for 
example, a Base-64 encoded image).  For our purposes, a JSON object is used to represent
an RFID interrogation record, as shown the example JSON listing.  
The contents of the `freeform` field are encrypted by the server prior 
to storage in the database, and decrypted when served back to a client if the correct 
password is provided with the request.  The password is not stored on the server; rather, 
it is used as the AES key to decrypt the value on each request.

The `interrogator_timestamp` and the supplied password parameter are used to 
set the initialization vector (IV) and password of the encryption module.  The framework
uses AES in Counter Mode (CTR) provided by the PyCrypto library.  
By re-initializing the IV with the most recent timestamp, 
we ensure that the IV and password are unique on each AES encryption.  

| ﻿Service Endpoint | Method | Description | Parameters | Return Body |
|--------------------------------|--------|------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| /api/iot/maxtime | GET | Obtain the maximum relative timestamp in the database | None | {"data": {"max_relative_timestamp": 500 }} |
| /api/iot/\<starttime\>/\<endtime\> | POST | Retrieve data between \<starttime\> and \<endtime\> timestamps | { "data": { "db_password": 'str'} } | {"data": [ {"id": 0, "absolute_timestamp": "5/13/2020 3:32 PM", relative_timestamp: 500, interrogator_timestamp: 10500, freeform: "..."} ]} |
| /api/iot/seconds/<n> | POST | Retrieve data from the last <n> seconds | { "data": { "db_password": 'str'} } | {"data": [ {"id": 0, "absolute_timestamp": "5/13/2020 3:32 PM", relative_timestamp: 500, interrogator_timestamp: 10500, freeform: "..."} ]} |
| /api/iot | PUT | Append data to the database | { "data": { "db_password": "str", "relative_time": 500, "interrogator_time": "3/18/2014 10:59:19.123456 AM", "freeform": "..."} } | HTTP 201 |
| /api/audit | GET | Retrieve the HIPAA audit log | None | {"data": [{"id":0, "absolute_timestamp": "5/13/2020 3:32 PM", "log": "…"}]} |

### Instructions (Running framework on localhost for testing/development)
Start the following components in the order presented below.
Note that some scripts may be in a scripts/ subdirectory.

#### Set up
Use a separate command window or tab for each of the following:

###### Start MySQLd
MySQL v5.7:
```
mysqld
```
MySQL v5.5 (Raspberry Pi):
```
sudo service mysql start
```
###### Web Server
Navigate to `database/`:
* `python3 server.py -d -e 0.75` (for a SQLite instance when running processing modules)
    * Other servers can be run via parameters to `server.py`, for example, `python3 server.py -d -m -s dbuser -w dbpass -b localhost -e 0.75` will start a MySQL instance
	* Run `service mysql start` as root if using MySQL and starting the MySQL server for the first time, and `destroy_and_initialize.sh` can be used to clear the database and instantiate the tables prior to use

###### IoT Sensor Device, i.e., RFID Interrogator
Navigate to `interrogator/` and run either of the following:
* `python3 client.py -i rfidreader.local -p encpassword -d` to use the Impinj Speedway R1000 RFID Reader
* `python3 client.py -i speedwayr-aa-bb-cc.local -p encpassword -g r420 -d -a 1 -l 0.75 -t 4` to use Impinj Speedway R420 RFID Reader
* `python3 client.py -i itemsense-server.local:80 -p encpassword -g xarray -d -l 0.75 -t 4 -u itemsenseuser -w itemsensepassword` to use Impinj xArray cluster

One of the parameters passed to these scripts is the IP address of the Impinj device.  You will want to supply the correct IP address or network name for the device.  In the case of the xArray, the IP address of the ItemSense server should be given; this server, in turn, communicates with the xArray devices specified in your Job.  The default facility name is MESS and the default job recipe name is IMPINJ_Fast_Location.  The recipe should be configured to use the xArray interrogators in use.  The username and password to ItemSense are also provided as parameters from the xarray script.

You can see the different configuration parameters used or eligible for use through the client scripts by entering: `python client.py -h`

#### Shutdown
1. Create a file called 'quit' in the directory running the server to terminate the web server.
2. Create a file called 'quit' in the directory running the interrogator to terminate the interrogator.
3. Run `killall mysqld` to terminate MySQL.
4. Remove any 'quit' files before running the software again.

#### Export to .db file
Before running the following, make sure MySQL and webserver are running.
* Navigate to `database/`
* Run `./export_mysql_to_sqlite.sh`
* This will create a database file named 'out.db1' in the current working
directory with data from the MySQL database.

#### Convert .db file to .csv
* Rename the output db file to `database.db`
```
mv out.db1 database.db
```
* Run: `./retrieve_wholedb_json.sh`
* This will create a file named `out.csv`. This file contains the collected RFID
tag data.

#### Remove collected data from MySQL database and re-initialize database
* Run: `./destroy_mysql.sh`. When prompted for a password, press enter.
* Run: `./initialize_mysql.sh`.

## Data Export Instructions
Following instructions below to export the collected data. Ensure shutdown steps
listed above have been completed before proceeding to export data:
1. Export MySQL database to SQL database: `./export_mysql_to_sqlite.sh`.
2. You will now have a file named `out.db1` in your working directory. If you
would like to export db files, proceed to step 6.
3. Rename db file: `mv out.db1 database.db`
4. Convert db file to csv: `./retrieve_wholedb_json.sh`.
5. You will now have a csv file named `out.csv` in your working directory.
6. If running the server on a remote computer such as a Raspberry Pi, copy your desired file (either `out.db1` or `out.csv`) from the server
Raspberry Pi to the Bellyband laptop by running the following on the computer being copied to:
    1. Open a terminal window.
    2. Navigate to your desired directory. For example, a folder on the Desktop:
    `cd ~/Desktop/data_dir`.
    3. Run:
    ```
    scp pi@192.168.0.105:/home/pi/database/<desired_file> .
    ```
    Where `<desired_file>` is either `out.db1` or `out.csv`.  Note in prior versions, the database/ directory was called rssi_db.
7. Rename your data file, for example: `mv out.csv breathing_30.csv`
8. Copy the file to a USB drive to export to your personal computer.

You have now completed data collection and export.
If you are done with data collection, close all terminal windows on the
Bellyband laptop by typing `exit` and pressing enter (for Raspberry Pi
terminals, you will need to do this twice for terminal window to close).
Shutdown the laptop by clicking the gear icon on the top right and selecting
shutdown. Finally, power down all devices at the IoT setup.

## Troubleshooting
* **Interrogator script hangs**: If the interrogator script hangs after quitting
or during data collection, do the following to kill the interrogator process:
    1. Press CTRL+Z
    1. Find the interrogator process ID: `ps -a`. The process ID will be listed
    next to `./client_r420.py` or something similar.
    1. Once you have obtained the process ID, kill it using
    `kill -9 <process_id>` (where `<process_id>` is the process ID you
    determined in the previous step without the angular brackets).

## Dependencies
* The Impinj R1000 driver uses a modified llrp_proto.py from the LLRPyC package, included in the interrogator directory.
    * License information can be found in llrp_proto.py
* The Impinj R420 driver uses a previously modified sllurp installation, and with sllurp updates is now compatible with a vanilla checkout.
    * License information can be found in sllrp/LICENSE.txt

## Limitations
* The Impinj interrogates between 30-120 per second, by observation, depending on the Mode and Tag Population parameters selected in the client driver file.
* The MySQL database freeform (i.e., json) record entry is limited to approximately 64K per entry after encryption and base64 encoding.
* The database module contains a test key and certificate for the server: do not use these in production, as they are made publicly available.  See the instructions above to generate your own web server certificate and key.  The interrogator client transmits SSL encrypted data based on this key, and the server in-turn uses the key as part of its at-rest encryption.
----

## Containerization
*TODO*: This section should be considered WIP. Add updates to this section until
the full software stack is capable or independently running containerized.

### Software Requirements
1. [Docker](https://www.docker.com/products/docker-engine)
2. [Docker Compose](https://docs.docker.com/compose/)

### Using the Containers
#### Container Build & Startup
```
$ docker-compose build
$ docker-compose up
```

#### Container Shutdown
```
$ docker-compose down
```

## Development Guidelines
### Formatting Python
Install the `autopep8` code formatting tool.
```
pip install autopep8
```
Run the following command from within the root directory of the repository.
```
autopep8 --in-place --recursive .
```
In the future we may want to use the `--aggressive` option to make
non-whitespace style changes.

## License
Copyright 2014 William M. Mongan
billmongan@gmail.com
See license for license information 
