#!/usr/bin/env python3

import pickle
import socket
import numpy as np
from scipy import signal
import threading

#classe che raccoglie i dati ricevuti dai diversi sensori attraverso i socket
class Database: 
    def __init__(self):
        self.conns = []
        self.data = []
        self.files = []
        self.l = threading.Lock()

    def band_pass_filter(s) -> np.ndarray:
        fs = 4000
        low_cut = 20
        high_cut = 1000
        nyq = fs / 2
        low = low_cut/nyq
        high = high_cut/nyq
        order = 2

        b,a = signal.butter(order, [low, high], "bandpass", analog=False)
        y = signal.filtfilt(b, a, s)

        return y
    
    def new_client(self,conn) -> int:
        with self.l:    # prende il lock sulla lista
            n = len(self.data)
            self.conns.append(conn)
            self.data.append([])
            self.files.append(open(f"{n}.csv","w"))
        return n

    def update(self,id,data):
        self.data[id].extend(data)
        if len(self.data[id])>2048:
            self.save_to_file(id)
            self.data[id].clear()
            
    def save_to_file(self,id):
        self.files[id].write(";".join(map(str,self.data[id]))+";")
        
    def close_client(self, id):
        self.files[id].close()
        self.conns[id].close()
        
    def close_all(self):
        for id in range(len(self.files)):
            self.files[id].close()
            self.conns[id].close()
            del(self.data[id])

def acceptation_thread(socket, database):
    while True:
        conn, addr = s.accept()
        threading.Thread(target=threaded_client, args=(conn, addr, database)).start()
        

def threaded_client(conn:socket.socket, addr, database: Database):
    id = database.new_client(conn)
    print(f"Il client {addr} si è connesso con ID={id}")

    while True:
        data = conn.recv(128)
        n = len(data)
        if n == 0:
            break
        print(f"ID={id} - Ricevuti {n} bytes")
        print(data)
        try:
            data_list = list(data)
            data_parsed = []
            for i in range(0, n, 2):
                data_parsed.append((data_list[i+1] << 8) + data_list[i])
        except Exception as e:
            print(e)
            print("Dati corrotti")
            continue
        print(f"ID={id} - Lunghezza vettore: {len(data_parsed)}")
        print(data_parsed)
        database.update(id, data_parsed)

    print(f"Il client {addr} si è disconnesso")
    print("Salvataggio file in corso...")
    database.close_client(id)
    print("Salvataggio completato")
    conn.close()

if __name__=="__main__":
    PORT = 3125
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        s.bind(("", PORT))
    except socket.error as e:
        print('ziopony')
        print(e)

    s.listen()
    print(f"Server avviato sulla porta {PORT}")

    database = Database()
    acc_thread = threading.Thread(target=acceptation_thread, args=(s,database), daemon=True)
    acc_thread.start()
    while True:
        try:
            esc = input()
        except KeyboardInterrupt:
            exit()
        if esc=="save":
            database.close_all()
        if esc!="":
            exit()

