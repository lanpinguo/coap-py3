import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('coapUtils')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())

import traceback
import re

#===== trimming zeros on addresses

def trimAddress(address):
    return re.sub(
        pattern = r':0+([0-9A-Fa-f]+)',
        repl    = r':\1',
        string  = address,
    )

#===== converting

def int2buf(val,length):
    returnVal  = []
    for i in range(length,0,-1):
        returnVal += [val>>(8*(i-1))&0xff]
    return returnVal

def buf2int(buf):
    returnVal  = 0
    for i in range(len(buf)):
        returnVal += buf[i]<<(8*(len(buf)-1-i))
    return returnVal

def buf2str(buf):
    if isinstance(buf,str):
        buf = buf.encode(encoding='utf-8')
    return buf

def str2buf(in_str):
    if isinstance(in_str,str):
        in_str = in_str.encode(encoding='utf-8')
    return in_str

#===== byte manipulation

def xorStrings(s1,s2):
    assert len(s1) == len(s2)
    if isinstance(s1,str):
        s1 = s2.encode(encoding='utf-8')
    if isinstance(s2,str):
        s2 = s2.encode(encoding='utf-8')
    return bytes((a ^ b) for a, b in zip(s1, s2))

def zeroPadString(s1, len):
    output = '{!s:\0>{width}}'.format(s1, width=len)
    #print(output)
    return output.encode(encoding='utf-8')

def flipFirstBit(s1):
    return xorStrings(s1, '\x80' + '\x00' * (len(s1) - 1))

#===== formatting

def formatBuf(buf):
    return '({0} bytes) {1}'.format(
        len(buf),
        '-'.join(['%02x'%b for b in buf])
    )

def formatCrashMessage(threadName,error):
    returnVal  = []
    returnVal += ['\n']
    returnVal += ['======= crash in {0} ======='.format(threadName)]
    returnVal += ['Error:']
    returnVal += [str(error)]
    returnVal += ['\ncall stack:\n']
    returnVal += [traceback.format_exc()]
    returnVal += ['\n']
    returnVal  = '\n'.join(returnVal)
    return returnVal

#===== header manipulation

def ipv6AddrString2Bytes(string):
    
    sidesString    = string.split('::')
    
    startString    = sidesString[0].split(':')
    if len(sidesString)>1:
        endString  = sidesString[1].split(':')
    else:
        endString   = []
    
    startBytes      = []
    for e in startString:
        startBytes += int2buf(int(e,16),2)
    endBytes        = []
    for e in endString:
        endBytes   += int2buf(int(e,16),2)
    
    rawbytes = startBytes + [0x00]*(16-len(startBytes)-len(endBytes)) + endBytes
    
    return rawbytes

#===== header manipulation

def carry_around_add(a, b):
    c = a + b
    return (c & 0xffff) + (c >> 16)

def checksum(byteList):
    s = 0
    for i in range(0, len(byteList), 2):
        w = byteList[i] + (byteList[i+1] << 8)
        s = carry_around_add(s, w)
    return ~s & 0xffff

def calcUdpCheckSum(srcIp,destIp,srcPort,destPort,payload):
        
    pseudoPacket  = []
    
    # IPv6 pseudo-header
    pseudoPacket += srcIp                         # Source address
    pseudoPacket += destIp                        # Destination address
    pseudoPacket += int2buf(8+len(payload),4)     # UDP length
    pseudoPacket += [0x00]*3                      # Zeros
    pseudoPacket += [17]                          # next header
    
    # UDP pseudo-header
    pseudoPacket += int2buf(srcPort, 2)           # Source Port
    pseudoPacket += int2buf(destPort, 2)          # Destination Port
    pseudoPacket += int2buf(len(payload), 2)      # Length
    pseudoPacket += [0x00,0x00]                   # Checksum
    
    pseudoPacket += payload
    if len(pseudoPacket)%2==1:
        pseudoPacket += [0x00]
    
    return checksum(pseudoPacket)
