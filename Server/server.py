#!/usr/bin/env python3

import pickle
import socket
import numpy as np
from scipy import signal
import threading
from controller import Controller

def acceptation_thread(s:socket.socket, controller:Controller):
    try:
        while True:
            conn, addr = s.accept()
            controller.new_client(conn, addr)
    except:
        pass
    finally:
        s.close()
        
if __name__=="__main__":
    PORT = 3125
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        s.bind(("", PORT))
    except socket.error as e:
        print(e)

    s.listen()
    print(f"Server avviato sulla porta {PORT}")

    controller = Controller()
    acc_thread = threading.Thread(target=acceptation_thread, args=(s,controller), daemon=True)
    acc_thread.start()
    while True:
        try:
            cmd = input()
        except KeyboardInterrupt:
            break
        if cmd.isnumeric(): #start per n secondi
            controller.start_all(int(cmd))
        
        #ESEMPIO NUOVO COMANDO
        #elif cmd == "nuovocmd":
        #    controller.send_all("nuovocmd")
        #    # per mandare bytes vedi riga 120 (funzione start_all del controller)
        
        elif cmd != "":   #esci scrivendo qualcosa a caso (no numeri)
            break
    controller.close_all()
    s.close()
    acc_thread.join()
