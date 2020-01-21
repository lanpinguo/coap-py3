import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('socketUdpReal')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())

import socket
import time
import select
from coap import socketUdp
import threading

class socketUdpReal(socketUdp.socketUdp):

    BUFSIZE = 1024
    
    def __init__(self,ipAddress,udpPort,callback):
        
        # log
        log.debug('creating instance')
        
        # initialize the parent class
        socketUdp.socketUdp.__init__(self,ipAddress,udpPort,callback)
        
        # change name
        self.name       = 'socketUdpRead@{0}:{1}'.format(self.ipAddress,self.udpPort)
        self.callback   = callback
        
        # local variables
        self.socketLock = threading.Lock()
        
        # open UDP port
        try:
            self.socket_handler  = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            # Use of 41 instead of socket.IPPROTO_IPV6 because it does not exist in python 2.7 for windows
            self.socket_handler.setsockopt(41, socket.IPV6_V6ONLY, 0)
            self.socket_handler.bind((self.ipAddress,self.udpPort))
        except socket.error as err:
            log.critical(err)
            raise
        except (AttributeError, ValueError):
            log.info('Your system does not support dual stack sockets. IPv4 is not enabled.')

        self.active = True
        
        # start myself
        self.start()
    
    #======================== public ==========================================
    
    def sendUdp(self,destIp,destPort,msg):
        
        # convert msg to string
        #msg = ''.join([chr(b) for b in msg]) #python2
        msg = bytearray(msg)                  #python3
        # send over UDP
        with self.socketLock:
            addrinfo = socket.getaddrinfo(destIp, destPort)
            self.socket_handler.sendto(msg,addrinfo[0][4])
        
        # increment stats
        self._incrementTx()
    
    def close(self):
        # declare that this thread has to stop
        self.active = False
        
        # wait for this thread to exit
        self.join()

    #======================== private =========================================
    def _socket_ready_handle(self, s):
        """
        Handle an input-ready socket

        @param s The socket object that is ready
        @returns 0 on success, -1 on error
        """

        if s and s == self.socket_handler:
            try:
                # blocking wait for something from UDP socket
                raw,conn = self.socket_handler.recvfrom(self.BUFSIZE)
            except socket.error as err:
                log.critical("socket error: {0}".format(err))
                return -1
            else:
                if not raw:
                    log.error("no data read from socket, stopping")
                    return -1
                if not self.active:
                    log.warning("active is false")
                    return -1

            timestamp = time.time()
            source    = (conn[0],conn[1])
            #data      = [ord(b) for b in raw] #python2
            data      = raw  #python3
            
            log.debug("got {2} from {1} at {0}".format(timestamp,source,data))
            
            #call the callback with the params
            self.callback(timestamp,source,data)
        else:
            log.error("Unknown socket ready: " + str(s))
            return -1

        return 0


    def run(self):
        epoll = select.epoll()
        epoll.register(self.socket_handler.fileno(), select.EPOLLIN)
        fd_to_socket = {self.socket_handler.fileno():self.socket_handler,}

        while self.active:
            events = epoll.poll(2)
            if not events:
                continue 

            for fd, event in events:    
                if event & select.EPOLLIN:   
                    sock = fd_to_socket[fd]
                    if self._socket_ready_handle(sock) != 0:
                        self.active = False
                        break
 
       # if you get here, we are tearing down the socket
        log.debug("closing ")
        epoll.unregister(self.socket_handler.fileno())
        epoll.close()       
        # close the socket
        self.socket_handler.close()
        
        # log
        log.info("teardown")
