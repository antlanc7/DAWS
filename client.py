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

while (1):
    buf.append(random.randint(0,4095))
    if len(buf)>=BUF_LEN:
        s.sendall(pickle.dumps(buf))
        buf.clear()
        time.sleep(1)
