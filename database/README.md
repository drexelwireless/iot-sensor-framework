# RFID Data Collection - MySQL Server

## Server Setup
From the host machine run the following:
```
$ docker-compose run database 
```

From within the container run the following:
```
./destroy_and_initialize.sh
```

## Server Cleanup
From within the container run the following:
```
service mysql stop
```
