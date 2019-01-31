# RFID Data Collection - MySQL Server

## Required Software
1. Docker Community Edition
2. Docker Compose

## Server Setup
From the host machine run the following:
```
$ docker-compose build
$ docker-compose up
$ docker-compose run rssi_db
```

From within the container run the following:
```
root:/rssi_db# service mysql start
root:/rssi_db# mysql -u root --password=bellyband
mysql> DROP DATABASE IF EXISTS rssidb;
mysql> CREATE USER IF NOT EXISTS rssi;
mysql> GRANT USAGE ON *.* TO rssi;
mysql> DROP USER rssi;
mysql> CREATE DATABASE rssidb;
mysql> CREATE USER rssi;
mysql> quit
root:/rssi_db# mysql -u root --password=bellyband rssidb
mysql> GRANT ALL PRIVILEGES ON rssidb TO rssi;
mysql> GRANT ALL PRIVILEGES ON *.* TO rssi;
mysql> SET PASSWORD FOR rssi  = PASSWORD('abc123');
mysql> quit
```

## Server Cleanup
From within the container run the following:
```
service mysql stop
```

From the host machine run the following:
```
docker-compose down
```
