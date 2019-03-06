#coding:utf-8

import socket
import binascii
import sys
import time
import thread
import threading


global connMap
connMap ={}
lock=threading.Lock()



class EquipmentManager(threading.Thread):
    def __init__(self, conn):
        threading.Thread.__init__(self)
        self.conn = conn
        self.client_answer =''
        self.quit = False
    
    def sendCmd(self,cmd):
        cmd +='\r\n'
        for c in cmd:
            self.conn.sendall(binascii.hexlify(c)+'\n')
        self.conn.sendall('\n\n')

 #infinite loop for reading and append the result to a global buffer
    def run(self):
        #print ("receving thread started")
        global connMap
        while self.quit != True:
            #try:
            data = self.conn.recv(8192)
            if not data:  
                    #client connection closed. remove it from map
                lock.acquire()
                for key in connMap:
                    if connMap[key] == self.conn:
                        del connMap[key]
                lock.release()        
                self.conn.close()
                break        
            #except KeyboardInterrupt:
             #   self.conn.close()
                #print(data)
                #print ("-----------------------------------")
            for line in data.splitlines():
                l = line.strip()
                #print("l is " + l)
                if l:
                    try:
                        raw = binascii.unhexlify(l)
                        self.client_answer+= raw+'\n'
                  #      print("raw is " + raw)
                    except:
                        print " format error", l
                #print ("client_answer is " + self.client_answer)

    def clearAnswer(self):
          self.client_answer =''

    def setQuit(self):
        self.quit = True

    def getName(self):
        for line in self.client_answer.splitlines():
            sys.stdout.write("line is " +line)
            l = line.strip()
            if l:
                if l.startswith('CE') or l.startswith('MX'):
                    return l
        return None            

    def logIt(self,logName,message):
        if logName !=None:
            f = open (logName,'a')
            f.write (message+'\n')
            f.close()
        else:
            print ("Equipment file name is None")    

def set_debug (equipM):
    equipM.start()
    #for clear the equipment buffer purpose
    time.sleep(3)
    equipM.sendCmd("")
    equipM.sendCmd("")
    equipM.clearAnswer() 
    retry =0
    while (retry <5):
        time.sleep(2)
        retry+=1  
        equipM.sendCmd("cat /s/name\n")
        time.sleep(5)
        equipName = equipM.getName()
        if equipName !=None:
            equipM.logIt(equipName, time.ctime() + " client connected")
            lock.acquire()
            connMap[equipName]=equipM.conn
            lock.release()
            retry = 10  #quit the loop
        else:
            print ("No Equipment name found!")
        
    if retry == 5:
        print("no equipment name found, quiting ")
        equipM.setQuit()
    else: 
        equipM.clearAnswer()
        equipM.sendCmd("rf -c shell\n")
        equipM.logIt(equipName,"rf -c shell " + "sent" )
        time.sleep(5)
        equipM.logIt(equipName, equipM.client_answer)
        equipM.clearAnswer()
        equipM.sendCmd("dlog -a 65535\n")
        equipM.logIt(equipName,"dlog -a 65535 " + "sent" )
        time.sleep(5)
        equipM.logIt(equipName, equipM.client_answer)
        equipM.setQuit()

def main(argv=None):
    #ip_port = ('127.0.0.1',2004)
    try:
        server_port =int (argv[1].strip())
    except:
        server_port = 2004
    ip_port = ('172.31.183.100',server_port)
    sk = socket.socket()
    sk.bind(ip_port)
    sk.listen(50)

    while True:
        #print ('v3 server waiting...')
        try:
            conn,addr = sk.accept()  
            print ("addr is =")
            print (addr)
        except KeyboardInterrupt:
            sk.close()
       
        try:
            emt = EquipmentManager(conn)
            thread.start_new_thread(set_debug,(emt,),)
        
        except KeyboardInterrupt:
            conn.close()
    
   
if __name__ == "__main__":
    sys.exit(main(sys.argv))
    