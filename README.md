# RFID Data Collection & Visualization Software  

This software suite contains scripts to collect and visualize RFID tag information using an Impinj Speedway RFID reader.

*Note: These instructions assume that the web server, interrogation and visualizer will be run on the same machine (IP addresses in all shell scripts have been set to `localhost`). For MESS Lab instructions, scroll to the bottom of this document or click [here](mess-lab-setup-instructions)*

### Requirements
The following software packages need to be installed before running RFID data collection. You will have to use the same install method (such as `pip install` or `easy_install`) listed here. Also, alternatives to using `sudo` for `pip install` are  `sudo -H pip install <package-name>` or `pip install --user <package-name>`. 

MySQL:
```
sudo apt-get install mysql-server-5.5
sudo mysql_secure_installation
sudo mysql_install_db
```

Other packages:
```
sudo apt-get install libmysqlclient-dev
sudo apt-get install python-dev
sudo pip install flask
sudo pip install MySQL-python
sudo apt-get install libcurl4-openssl-dev
sudo apt-get install libssl-dev
sudo apt-get install libffi-dev
export PYCURL_SSL_LIBRARY=openssl
sudo pip install pycurl --global-option="--with-openssl"
sudo pip install pycrypto
sudo pip install python-dateutil
sudo pip install httplib2
sudo pip install twisted
sudo pip install service_identity
sudo apt-get install python-matplotlib
sudo apt-get install libblas-dev liblapack-dev libatlas-base-dev gfortran
pip install scipy

# for client packages
sudo pip install pandas
sudo easy_install pykalman
sudo easy_install filterpy
sudo pip install statsmodels
sudo pip install scikit-learn
sudo apt-get install libfreetype6-dev libpng3
sudo pip install --upgrade pip
sudo pip install --upgrade filterpy # this upgrades numpy / scipy stack
sudo pip install git+https://github.com/ajmendez/PyMix.git
```

### Instructions (Running framework on localhost for testing/development)
Start the following components in the order presented below:

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
Navigate to `rfid_v6/rfid/v6/rssi_db/`:
* Run `./server_mysql.sh` (for use with the interrogator and MySQL) or `./server.sh` (for a SQLite instance when running processing modules)

###### RFID Interrogator
Navigate to `rfid_v6/rfid/v6/interrogator/` and run either of the following:
* `client_r1000.sh` to use the Impinj Speedway R1000 RFID Reader
* `client_r420.sh` to use Impinj Speedway R420 RFID Reader

###### Visualizer
Navigate to `visualizer_v1/v1/` and run either of the following:
* `live.sh` for a live visualizer.
* `simulate.sh` for a simulation of previously collected data.

#### Shutdown
1. In the command window running the visualizer, type 'q' and press enter.
1. Type 'q' and press enter to terminate the web server.
1. Type 'q' and press enter to terminate the interrogator.
1. Run `killall mysqld` to terminate MySQL.

#### Export to .db file
Before running the following, make sure MySQL and webserver are running.
* Navigate to `rfid_v6/rfid/v6/rssi_db/`
* Run `./export_mysql_to_sqlite.sh`
* This will create a database file named 'out.db1' in the current working directory with data from the MySQL database.

#### Convert .db file to .csv
* Rename the output db file to `database.db`
```
mv out.db1 database.db
```
* Run: `./retrieve_wholedb_json.sh`
* This will create a file named `out.csv`. This file contains the collected RFID tag data.

#### Remove collected data from MySQL database and re-initialize database
* Run: `./destroy_mysql.sh`. When prompted for a password, press enter.
* Run: `./initialize_mysql.sh`.

#### Run a processing module
* Change into the `fusionframework_v1` directory (or `fusionframework_v2` or other processing unit as appropriate)
* Run `./simulate.sh sensor_test.TestSensor` (replace with `sensor_your.YourSensor` for a YourSensor class written into the sensor_your.py file)

# MESS Lab Setup Instructions
## Data Collection 
Follow these instructions to collect data in the MESS lab RFID setup. 
1. Power up RFID Reader, Laptop and Raspberry Pis. All these devices are connected to a single power strip. 
2. Ensure the laptop is connected to port 5 on the CISCO switch via Ethernet. 
3. On the laptop, login to the `bellyband` account using the password: `kapilrocks`. 
4. Open two terminal windows (CTRL + ALT + T or from left dock). One will be used as the server and the other will run the interrogator scripts. 
5. On the server terminal: 
	1. Type `spi` and press enter. 
	1. Change directory: `cd rssi_db`
	1. You are now in the server scripts directory. Before starting data collection, run `./destroy_and_initialize.sh` (Password: `S1mbaby`) to remove all previously collected data. This should be done before every data collection session.  
	1. Run the server using `./server_mysql.sh`. You will also find scripts to convert db files in the same folder. Instructions for these are in the sections above. 
6. On the interrogator terminal: 
	1. Type `ipi` and press enter. 
	1. Change directory: `cd interrogator`
	1. Run interrogation: `./client_r420.sh`. Verify operation by placing an RFID tag in front of the interrogating antenna and watch for scrolling text indicating that a tag is being read. 
7. During data collection, use the following for real-time visualization: 
	1. Open a new terminal window on the Bellyband Laptop. 
	1. Type `workon bellyband` and press enter. 
	1. Change directory: `cd bellyband_software_framework/visualizer_v1/v1/`
	1. Before starting the visualizer make sure the server and interrogator scripts are running. Run the visualizer using: `./live.sh`
8. Shutdown instructions: 
	1. First shutdown the visualizer (if you are running it) by entering `q` in the visualizer terminal. 
	1. Next, shutdown the interrogator by entering `q` in the interrogator terminal. 
	1. Shutdown the server by entering `q` in the server terminal. 
	1. To export data, refer to the [Data Export Instructions](data-export-instructions) section below. 
	1. In case of issues, refer to the [Troubleshooting](troubleshooting) section below. 
9. To start another data collection round, repeat steps 5 to 8. Make sure you export collected data and copy to a different location using the instructions in [Data Export Instructions](data-export-instructions) before starting another data collection round. 
## Data Export Instructions 
Following instructions below to export the collected data. Ensure shutdown steps listed above have been completed before proceeding to export data:
1. Export MySQL database to SQL database: `./export_mysql_to_sqlite.sh`. 
2. You will now have a file named `out.db1` in your working directory. If you would like to export db files, proceed to step 6.  
3. Rename db file: `mv out.db1 database.db`
4. Convert db file to csv: `./retrieve_wholedb_json.sh`. 
5. You will now have a csv file named `out.csv` in your working directory. 
6. Copy your desired file (either `out.db1` or `out.csv`) from the server Raspberry Pi to the Bellyband laptop by running the following on the Bellyband Laptop: 
	1. Open a terminal window. 
	1. Navigate to your desired directory. For example, a folder on the Desktop: `cd ~/Desktop/data_dir`. 
	1. Run: 
	```
	scp pi@192.168.0.105:/home/pi/rssi_db/<desired_file> . 
	``` 
	Where `<desired_file>` is either `out.db1` or `out.csv`. 
7. Rename your data file, for example: `mv out.csv breathing_30.csv`
8. Copy the file to a USB drive to export to your personal computer. 

You have now completed data collection and export. If you are done with data collection, close all terminal windows on the Bellyband laptop by typing `exit` and pressing enter (for Raspberry Pi terminals, you will need to do this twice for terminal window to close). Shutdown the laptop by clicking the gear icon on the top right and selecting shutdown. Finally, power down all devices at the RFID setup. 

## Troubleshooting 
* **Interrogator script hangs**: If the interrogator script hangs after quitting or during data collection, do the following to kill the interrogator process: 
	1. Press CTRL+Z
	1. Find the interrogator process ID: `ps -a`. The process ID will be listed next to `./client_r420.py` or something similar. 
	1. Once you have obtained the process ID, kill it using `kill -9 <process_id>` (where `<process_id>` is the process ID you determined in the previous step without the angular brackets). 
