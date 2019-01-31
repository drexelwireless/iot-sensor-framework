# RFID Data Collection - Interrogator

## Required Software
1. Docker Community Edition
2. Docker Compose

## Interrogator Setup
From the host machine run the following:
```
$ docker-compose build
$ docker-compose up
$ docker-compose run interrogator
```

From within the container run the following:
##### Impinj Speedway Revolution R420
```
root:/interrogator# ./client_r420.sh
```
##### Impinj Indy R1000
```
root:/interrogator# ./client_r1000.sh
```

## Interrogator Cleanup
From the host machine run the following:
```
docker-compose down
```
