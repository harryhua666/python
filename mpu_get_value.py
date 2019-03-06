import smbus
import math
import socket
import time
import numpy as np
import threading



# Power management registers
power_mgmt_1 = 0x6b
power_mgmt_2 = 0x6c    
accel_xout_scaled = 0.0
accel_yout_scaled = 0.0
accel_zout_scaled = 0.0
obs_list = []
list_lock = threading.Lock()

s = socket.socket()
host = '192.168.43.7'
port = 5000
s.connect((host,port))
standard_pos = 0.0
threshold_pos = 0.0

def read_byte(adr):
    return bus.read_byte_data(address, adr)

def read_word(adr):
    high = bus.read_byte_data(address, adr)
    low = bus.read_byte_data(address, adr+1)
    val = (high << 8) + low
    return val

def read_word_2c(adr):
    val = read_word(adr)
    if (val >= 0x8000):
        return -((65535 - val) + 1)
    else:
        return val

def dist(a,b):
    return math.sqrt((a*a)+(b*b))

def get_y_rotation(x,y,z):
    radians = math.atan2(x, dist(y,z))
    return -math.degrees(radians)

def get_x_rotation(x,y,z):
    radians = math.atan2(y, dist(x,z))
    return math.degrees(radians)

def add_to_obs_list(acc_z_scaled):
    global obs_list, list_lock
    acc_z_scaled = abs(acc_z_scaled)
    if (acc_z_scaled > 1.3 or acc_z_scaled < 0.2): #abnormal value or state 
        return
    if list_lock.acquire(): 
        obs_list.append(acc_z_scaled)
        list_lock.release()

def get_mvalue():
    global obs_list
    if list_lock.acquire(): 
        mean_value = np.mean(obs_list)
        std_dev = np.std(obs_list)
        if len(obs_list) <10:
            msg = 'too few items for determing value, ignoring \n' 
            s.sendall (bytes(msg, 'utf-8'))
            result =-1.0     
        elif std_dev >0.2:  #deviation too large, possibly moving, ignore this observation
            msg = 'devation is ' + str(std_dev) + ' is larger than 0.2, moving. ignored for values\n' 
            s.sendall (bytes(msg, 'utf-8'))
            result = -1.0
        else:
            result = mean_value
        
        obs_list =[]
        list_lock.release() 
        return result

class myThread (threading.Thread):
    def __init__(self, sock):
        threading.Thread.__init__(self)
        self.s = sock
        self.END = '\n'

    def run(self):
        global standard_pos, threshold_pos
        print ('thread started')
        while True:
            if (standard_pos > 0 and threshold_pos > 0):   #the parameter has been set
                break 
            data = self.s.recv(1024)
            if not data:
                break
            for line in data.splitlines():
                print (line)
                print (line.decode())
                if line.decode() =='1':
                    std_pos =get_mvalue()
                    while std_pos < 0.0:
                        time.sleep(5)
                        std_pos = get_mvalue
                    standard_pos = std_pos
                    print ('standard pos = ', standard_pos)
                elif line.decode() == '2':
                    thr_pos = get_mvalue()
                    while thr_pos <0.0:
                        time.sleep(5)
                        thr_pos = get_mvalue()
                    threshold_pos =thr_pos
                    print ('threshold pos = ', threshold_pos)
                else:
                    time.sleep(1)



def judge():
    global  obs_list, s, list_lock, standard_pos
    if standard_pos > 0.0 and threshold_pos > 0.0:
        mean_value = get_mvalue()
        if mean_value>0:
            if abs( (standard_pos - mean_value)/standard_pos) < 0.03 : #position OK
                msg = 'mean position is ' + str(mean_value) + ' and is within range\n'
                s.sendall (bytes(msg, 'utf-8'))  
            else:
                #it needs to be alarmed
                msg = 'mean position is ' + str(mean_value) + 'and is out of range \n'
                s.sendall (bytes(msg, encoding='utf-8'))
    global timer 
    timer = threading.Timer(5,judge)   #5秒后再judge一次
    timer.start() 

bus = smbus.SMBus(1) # or bus = smbus.SMBus(1) for Revision 2 boards
address = 0x68       # This is the address value read via the i2cdetect command

# Now wake the 6050 up as it starts in sleep mode
bus.write_byte_data(address, power_mgmt_1, 0)
timer = threading.Timer(7,judge)  #首次启动
timer.start()
set_std_thread = myThread(s)
set_std_thread.start()

while True:
    #print ("gyro data")
    #print ("---------")

    gyro_xout = read_word_2c(0x43)
    gyro_yout = read_word_2c(0x45)
    gyro_zout = read_word_2c(0x47)

    #print ("gyro_xout: ", gyro_xout, " scaled: ", (gyro_xout / 131))
    #print ("gyro_yout: ", gyro_yout, " scaled: ", (gyro_yout / 131))
    #print ("gyro_zout: ", gyro_zout, " scaled: ", (gyro_zout / 131))

    #print()
    #print ("accelerometer data")
    #print ("------------------")

    accel_xout = read_word_2c(0x3b)
    accel_yout = read_word_2c(0x3d)
    accel_zout = read_word_2c(0x3f)

    accel_xout_scaled = accel_xout / 16384.0
    accel_yout_scaled = accel_yout / 16384.0
    accel_zout_scaled = accel_zout / 16384.0
    add_to_obs_list (accel_zout_scaled)
    #print ("accel_xout: ", accel_xout, " scaled: ", accel_xout_scaled)
    #print ("accel_yout: ", accel_yout, " scaled: ", accel_yout_scaled)
    print ("accel_zout: ", accel_zout, " scaled: ", accel_zout_scaled)

    #print ("x rotation: " , get_x_rotation(accel_xout_scaled, accel_yout_scaled, accel_zout_scaled))
    #print ("y rotation: " , get_y_rotation(accel_xout_scaled, accel_yout_scaled, accel_zout_scaled))
    strs = str(accel_xout_scaled)+ ',' + str(accel_yout_scaled)+ ','+ str(accel_zout_scaled) +'\n'
    #s.sendall(bytes(strs, encoding='utf-8'))
    time.sleep(0.2)
