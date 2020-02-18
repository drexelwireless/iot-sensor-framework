# RFID Data Collection - Interrogator

## Interrogator Setup
From the host machine run the following:
```
$ docker-compose run interrogator
```

From within the container run the following:
##### Impinj Speedway Revolution R420
```
user:/interrogator$ python3 client.py -i speedwayr-aa-bb-cc.local -p encpassword -g r420 -d -a 1 -l 0.75 -t 4
```
##### Impinj Indy R1000
```
user:/interrogator$ python3 client.py -i rfidreader.local -p encpassword -d
```
