#!/usr/bin/python
# -*- coding: utf-8 -*-
#
import logging
import logging.handlers
import sys
import SocketServer
import time
import datetime
import select
import getopt
import os
import signal
import operator
import shutil
import re
from collections import namedtuple
try:
    import cPickle as pickle
except:
    import pickle
from POSHandler import *

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s')
#
rtfile  = logging.handlers.RotatingFileHandler("./tk102.log",maxBytes=1024*1024*10, backupCount=5)
console = logging.StreamHandler()
#
glogger = logging.getLogger('TK102')
rtformat='%(asctime)s %(levelname)-8s %(message)s'
rtformatter = logging.Formatter(fmt=rtformat)
rtfile.setFormatter(rtformatter)
glogger.addHandler(rtfile)
glogger.propagate = False #stop console log for this one
# Set up console
cformat='%(asctime)s %(message)s'
cformatter = logging.Formatter(fmt=cformat, datefmt="%Y%m%d %H:%M:%S")
console.setFormatter(cformatter)
console.setLevel(logging.INFO)
glogger.addHandler(console)
#

Pos = namedtuple('Pos', 'imei, lat, lon, spd, bearing, acc, idx')

class TK102RequestHandler(SocketServer.BaseRequestHandler):
    def __init__(self, request, client_address, server):
        self.logger = glogger #logging.getLogger('TK102Handler')
        self.logger.debug('New request')
        SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)
        return

    def debug(self, msg):
        self.logger.debug("[%s] "+str(msg), self.imei)

    def info(self, msg):
        self.logger.info("[%s] "+str(msg), self.imei)

    def error(self, msg):
        self.logger.error("[%s] "+str(msg), self.imei)

    def on_start(self):
        """
        Called when a new tracker is initialized.
        """
        if self.poshandler:
            self.poshandler.on_start()

    def on_finish(self):
        """
        Called before the thread exits.
        """
        if self.poshandler:
            self.poshandler.on_finish()

    def on_msg(self, msg):
        if self.poshandler:
            self.poshandler.on_msg(str(msg))

    def on_position(self):
        """
        Called everytime we receive a GPS position string.
        """
        if self.poshandler:
            self.poshandler.on_position()

    def on_stationary(self):
        """
        Called if last two positions are the same. To be implemented.
        """
        if self.poshandler:
            self.poshandler.on_stationary()

    def on_start_move(self):
        """
        Called if moving again after stationary destection. To be implemented.
        """
        if self.poshandler:
            self.poshandler.on_start_move()

    def send(self, msg):
        self.debug('send: '+msg)
        self.request.send(msg+"\n")
        self.bytes_s += len(msg)+1

    def handle(self):
        self.server.socket.setblocking(0)
        #self.server.socket.settimeout(10.0)
        cur_pid         = os.getpid() #threading.current_thread() 
        self.logger.info("handle start, pid: "+str(cur_pid))
        self.loop       = True
        self.counts     = 120
        self.counter    = self.counts
        self.last       = time.time()
        self.pid        = str(cur_pid)
        self.imei       = "PID: "+self.pid     #until we get the real one
        self.url        = ""
        self.ctldir     = "tk102pid_"+self.pid
        self.lastfile   = self.ctldir+"/last"  #touched, for timestamp
        self.cmdfile    = self.ctldir+"/cmd"   #reads a command from this file if it exists
        self.imeifile   = self.ctldir+"/imei"  #contains imei nr
        self.infofile   = self.ctldir+"/info"  #contains last lat,lon,... (pickled)
        self.bytesfile  = self.ctldir+"/bytes" #contains bytes received/sent (pickled)
        self.exitfile   = self.ctldir+"/exit"  #written on tracker exit/disappearance
        self.lat        = 0
        self.lon        = 0
        self.spd        = 0
        self.bearing    = 0
        self.acc        = 0
        self.pos        = None
        self.bytes_r    = 0
        self.bytes_s    = 0
        self.posidx     = 0 # number of positions received
        self.poshandler = None

        # create control dir
        try:
            if not os.path.exists(self.ctldir):
                os.mkdir(self.ctldir)
                self.debug("created "+self.ctldir)
            else:
                self.info("ctldir existed.")
        except:
            self.logger.error("[%s] Could not create dir ["+self.ctldir+"]", self.imei)
            self.loop = False
        #create last file
        try:
            fp_last = open(self.lastfile, 'w')
            fp_last.write(str(cur_pid))
            fp_last.close()
        except:
            self.error("Could not create 'last' file.")
            self.loop = False
        #
        # LOOP
        #
        while self.loop:
            sdata = ""
            try:
                sdata = self.request.recv(1024)
                if not sdata:
                    self.error("Not data.")
                    self.counter = 0
            except socket.error as err:
                if str(err) == "[Errno 35] Resource temporarily unavailable":
                    time.sleep(0.1) #OS X bug workaround
                    continue
                self.error("Socket error.")
                self.counter = 0
            if sdata == "":
                self.counter = self.counter - 1
            else:
                self.bytes_r += len(sdata)
                sdata = sdata.rstrip()
                self.debug("recv("+sdata+")")

            # If '\n' in data more than once we have more lines.
            lc = 0
            for data in sdata.split('\n'):
                data = data.rstrip()
                self.info("line["+str(lc)+"]: ("+data+")")
                lc += 1

                # "##,imei:35971004071XXXX,A;
                if data[0:7] == "##,imei": # FIRST CONTACT
                    imei_re = re.compile("##,imei:(\d+),A;")
                    m = imei_re.match(data)
                    if m:
                        self.imei = m.group(1)
                    self.logger = glogger
                    self.info("Init: imei "+self.imei)
                    # create imei file
                    try:
                        fp_imei = open(self.imeifile, 'w')
                        fp_imei.write(self.imei)
                        fp_imei.close()
                    except:
                        self.error("Could not create 'imei' file")
                        self.loop = False
                    #os.utime(last, None)
                    self.send("LOAD")
                    # 
                    for (rex, out_str) in startups:
                        if re.match(rex, self.imei):
                            self.debug('Found startup entry.')
                            cmd = out_str.replace("IMEI", self.imei)
                            self.send(cmd)
                    #
                    self.last = time.time()
                    self.counter = self.counts
                    self.poshandler = POSHandler( self ) 
                    self.on_start()

                elif data == self.imei+";": #"35971004071XXXX;":
                    self.send("ON")
                    self.last = time.time()
                    self.counter = self.counts
                    os.utime(self.lastfile, None)
                #imei:35971004071XXXX,tracker,1212220931,,F,083137.000,A,5620.2932,N,01253.7255,E,0.00,0;
                #imei:35971004071XXXX,tracker,000000000,,L,,,177f,,a122,,,;
                # check for L(ost) of F(ix) maybe also?  ^
                elif data[0:4] == "imei":
                    data = data[:-1] #remove ;
                    parts = data.split(',')
                    if len(parts) > 11:
                        self.last = time.time()
                        self.counter = self.counts
                        os.utime(self.lastfile, None) #mark OK
                        #print parts[7],parts[8],parts[9],parts[10]
                        #
                        # parse messages "help me", "et", etc?
                        # imei:35971004071XXXX,et,1304041745,,F,164528.000,A,5150.6452,N,00551.9452,E,0.00,0;
                        # imei:35971004071XXXX,help me,1304041743,,F,164345.000,A,5150.6452,N,00551.9452,E,0.00,0;
                        # imei:35971004071XXXX,tracker,1304041747,,F,164726.000,A,5150.6452,N,00551.9452,E,0.00,0;
                        if parts[8] != "":
                            #5620.2932 = ddmm.mmmm
                            #
                            ddmmmmmm = float(parts[7])
                            degs = int(ddmmmmmm / 100)
                            mins = ddmmmmmm - (degs*100)
                            lat = degs + mins/60
                            if parts[8] == "S":
                                lat = -lat
                            self.lat = round(lat, 5)
                            ddmmmmmm = float(parts[9])
                            degs = int(ddmmmmmm / 100)
                            mins = ddmmmmmm - (degs*100)
                            lon = degs + mins/60
                            if parts[10] == "W":
                                lon = -lon
                            self.lon = round(lon, 5)
                            #
                            self.spd = float(parts[11])*0.44704 #mi/h,to km/h,to m/s
                            self.bearing = -1
                            if parts[12] != "":
                                self.bearing = parts[12]
                            #
                            #'imei, lat, lon, spd, bearing, acc
                            self.pos = Pos(self.imei, self.lat,self.lon,self.spd,self.bearing,self.acc,self.posidx)
                            with open(self.infofile, "w") as f:
                                pickle.dump(self.pos, f)
                            self.on_position()
                            self.posidx += 1
                            #
                            msg = parts[1]
                            if msg != "tracker": #could be SOS, battery low, etc.
                                self.on_msg(msg)
                else:
                    self.info(data)
                time.sleep(.1)
                #
                if self.counter <= 0:
                    self.debug("Count-out, exiting")
                    self.loop = False
                # Check for a command in cmd file
                if self.cmdfile and os.path.exists(self.cmdfile):
                    try:
                        fp_cmd = open(self.cmdfile, 'r')
                        cmd = fp_cmd.readline()
                        cmd = cmd[0:-1]
                        fp_cmd.close()
                        new_cmd = self.cmdfile+"_"+str(int(time.time()))
                        #os.unlink(self.cmdfile) #or move to "cmd_timestamp"
                        shutil.move(self.cmdfile, new_cmd)
                        self.debug("cmd moved to "+new_cmd)
                        if cmd[0:1] == 'C':
                            sec = int(cmd[1:])
                            cmd = "**,imei:"+self.imei+",C,"+str(sec)+"s"
                            self.info(cmd)
                            time.sleep(1)
                            self.request.send(cmd+"\n")
                            self.bytes_s += (len(cmd) + 1)
                        if cmd[0:1] == 'E': #clear "help me" message
                            cmd = "**,imei:"+self.imei+",E"
                            self.info(cmd)
                            time.sleep(1)
                            self.request.send(cmd+"\n")
                            self.bytes_s += (len(cmd) + 1)
                        if cmd[0:1] == 'G': #clear "help me" message
                            cmd = "**,imei:"+self.imei+",G"
                            self.info(cmd)
                            time.sleep(1)
                            self.request.send(cmd+"\n")
                            self.bytes_s += (len(cmd) + 1)
                    except:
                        self.error("Could not handle 'cmd' file.")
                # Write receive/send stats
                with open(self.bytesfile, "w") as f:
                    pickle.dump((self.bytes_r, self.bytes_s), f)

        self.info('handle ready')
        return

    def finish(self):
        self.info('handle finish')
        self.on_finish()
        try:
            fp_exit = open(self.exitfile, 'w')
            fp_exit.write(self.imei)
            fp_exit.close()
        except:
            self.error("Could not create 'exit' file")
        self.info( "bytes read="+str(self.bytes_r)+" bytes sent="+str(self.bytes_s)+" points="+str(self.posidx) )
        return SocketServer.BaseRequestHandler.finish(self)

class TK102Server(SocketServer.ForkingMixIn, SocketServer.TCPServer):
    timeout             = 10
    daemon_threads      = True
    allow_reuse_address = True

def determine_td(d):
    """
    Difference between ctime of imei file (on creation) and the last
    access time of the last file is the total running time.
    """
    td0 = 0
    td1 = 0
    if os.path.exists(d+"/last"):
        td0 = int(float(os.stat(d+"/last").st_atime))
    if os.path.exists(d+"/imei"):
        td1 = int(float(os.stat(d+"/imei").st_ctime))
    td = abs(td0 - td1)
    return td

def on_exit(imei):
    """
    Called when the tread is killed/tracker disappeared.
    """
    ph = POSHandler( None )
    ph.on_exit(imei)

if __name__ == '__main__':
    import socket
    import threading

    #startups = { ("35971004071XXXX", "**,imei:IMEI,C,300s") ]
    startups = [ ("\d+" , "**,imei:IMEI,C,300s") ] #if imei matches, send string, replaces IMEI with real imei.

    # Remove left over directories form last time.
    dirs = os.listdir(".")
    for d in dirs:
        if d[0:9] == "tk102pid_":
            glogger.info("RMDIR: "+d)
            td = determine_td(d)
            glogger.info("Time delta: %s", str(datetime.timedelta(seconds=td)))
            shutil.rmtree(d)

    PORT     = 9000
    address  = ('', PORT) 
    server   = TK102Server(address, TK102RequestHandler)
    ip, port = server.server_address 

    t = threading.Thread(target=server.serve_forever)
    t.setDaemon(True) # don't hang on exit
    t.start()
    glogger.info('Server loop running in process:'+str(os.getpid()))

    tout = 180 #tracker timeout, 2x90 seconds
    
    while True:
        try:
            time.sleep(1)
            # Check our directories
            dirs = os.listdir(".")
            for d in dirs: #Loop over our tk102pid_nnn directories
                if d[0:8] == "tk102pid":
                    if not os.path.exists(d+"/last"): #not live
                        continue 
                    if os.path.exists(d+"/exit"): #was killed/exited
                        continue
                    # time between now and last sign of life:
                    td = int(time.time()-float(os.stat(d+"/last").st_atime))
                    if (td > 0 and operator.mod(td,91) == 0) or (td > tout):
                        glogger.debug(d+":"+str(td)) #already 91 seconds without update
                    if td >= tout+2: #we timed out, consider the tracker dead
                        # td between imei and last file is running/alive time
                        # of tracker. Time taken from file's timestamp.
                        td = determine_td(d)
                        glogger.info("Tracker gone after: %s", str(datetime.timedelta(seconds=td)))
                        #
                        f = open(d+"/last", 'r')
                        tpid = int(f.readline())
                        f.close()
                        # write in info table that tracker died here? imei?
                        glogger.info("No more data from tracker (%s).", str(tpid))
                        f = open(d+"/imei", 'r')
                        imei = "invalid"
                        try:
                            with open(d+"/imei", "r") as f:
                                imei = str(f.readline())
                        except:
                            glogger.exception("Could not read 'imei' file.")
                        glogger.debug("Killing: "+str(tpid)+" imei "+str(imei))
                        try:
                            os.kill(tpid, signal.SIGTERM)
                        except:
                            glogger.error("Could not kill process "+str(tpid)) #probably already gone
                        #
                        on_exit(imei)
                        # create killed file
                        try:
                            fp_killed = open(d+"/exit", 'w')
                            fp_killed.write(str(tpid))
                            fp_killed.close()
                        except:
                            glogger.exception("Could not create 'exit' file.")
                        # read nr bytes
                        try:
                            with open(d+"/bytes", "r") as f:
                                (bytes_r, bytes_s) = pickle.load(f)
                            glogger.info( str(imei)+": bytes read="+str(bytes_r)+" bytes sent="+str(bytes_s))
                        except:
                            glogger.exception("Could not read 'bytes' file.")
        except KeyboardInterrupt:
            sys.exit(0)
