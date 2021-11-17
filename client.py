#!/usr/bin/env python3

import socket
import random
import time
import pickle

PORT = 3125
BUF_LEN = 64

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.connect(("localhost",PORT))

buf = []
i = 0
dt = 0
while True:
    msg = s.recv(128)
    print(msg)
    if msg:
        cmd = list(msg)
        print(cmd)
        if cmd[0]==1:
            dt = cmd[1]
            t = time.time()
            while (time.time()-t<dt):
                acq = random.randint(0,4095)
                buf.append(acq % 256)
                buf.append(acq >> 8)
                i+=1
                if i>=BUF_LEN:
                    s.sendall(bytearray(buf))
                    buf.clear()
                    i=0
                time.sleep(0.5/1000)
            s.sendall("stop".encode())
    else:
        s.close()
        break
