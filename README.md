source code will be uploaded shortly

# tk102-server

Server to handle the GPS strings sent by tk102-2/B compatible GPS trackers (tk103, tk104 ?).

The python script listens on a port and handles connections. 

## Implements the following protocol:

0. tracker sends: <code>##,imei:\_IMEI\_,A;</code>
1. server responds: <code>LOAD</code>
2. tracker sends: <code>\_IMEI\_;</code>
2. server responds: <code>ON</code>

OR

2. tracker sends: <code>imei:\_IMEI\_,tracker,1212220931,,F,083137.000,A,5620.2932,N,01253.7255,E,0.00,0;</code>
2. coordinates and other values are calculated and stored.

If server does not receive <code>\_IMEI\_;</code> every 90 seconds, it times out (after 182 seconds), and exits the
thread handling the tracker. 

## Sending commands

* cmd  : read by the thread for commands. After a command is read, the cmd file is copied to cmd_TIMESTAMP where TIMESTAMP is the current unix epoch timestamp. For example, <code>'echo "C600" > cmd'</code> sets the interval on the tracker to 10 minutes. It sends the command: <code>**,\_IMEI\_,C,600s</code> to the tracker. The following are implemented:

1. Cnnn : sets tracker interval to nnn seconds
2. E    : clears alarm message
3. G    : sets move alarm

## Bookkeeping

Every new thread creates a tk102pid_PID directory which contains the following bookkeeping information:

last
:    contains the PID of the process, the file's timestamp is used by main thread to check
timeout. Each time a heart beat is received, the file is 'touched'.
imei
:    contains the trackers imei number.
info
:    last lat/lon/... received by tracker, in Python "pickle" format.
bytes
:    total number of bytes received by and sent to the tracker.

## Other

Protocol partly from [this google doc](https://docs.google.com/spreadsheet/ccc?key=0AtQofkYKWsMudDVHTi1ZNjI4emxlTVlhc3V1RWpsc0E#gid=0)
