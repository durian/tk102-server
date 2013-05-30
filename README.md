# tk102-server

Server to handle the GPS strings sent by tk102-2/B compatible GPS trackers.

The python script listens on a port and handles connections. 

## Implements the following protocol:

0. tracker sends: ##,imei:_IMEI_,A;
1. server responds: LOAD
2. tracker sends: _IMEI_;
2. server responds: ON

OR

2. tracker sends: imei:_IMEI_,tracker,1212220931,,F,083137.000,A,5620.2932,N,01253.7255,E,0.00,0;
2. coordinates and other values are calculated and stored.

If server does not receive _IMEI_; every 90 seconds, it times out (after 182 seconds), and exits the
thread handling the tracker. 

## Sending commands

cmd  : read by the thread for commands. After a command is read, the cmd file is copied to cmd_TIMESTAMP where TIMESTAMP is the current unix epoch timestamp. For example, 'echo "C600" > cmd' sets the interval on the tracker to 10 minutes. It sends the command: **,_IMEI_,C,600s to the tracker. The following are implemented:

* Cnnn : sets tracker interval to nnn seconds
* E    : clears alarm message
* G    : sets move alarm

## Bookkeeping

Every new thread creates a tk102pid_PID directory which contains the following bookkeeping information:

last
:  contains the PID of the process, the file's timestamp is used by main thread to check
timeout. Each time a heart beat is received, the file is 'touched'.

imei
:  contains the trackers imei number.

info
:  last lat/lon/... received by tracker, in Python "pickle" format.

bytes
:  total number of bytes received by and sent to the tracker.

## Other

Protocol partly from: https://docs.google.com/spreadsheet/ccc?key=0AtQofkYKWsMudDVHTi1ZNjI4emxlTVlhc3V1RWpsc0E#gid=0
