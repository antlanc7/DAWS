#!/usr/bin/env python3

import pickle
import socket
import numpy as np
from scipy import signal
import threading

#classe che raccoglie i dati ricevuti dai diversi sensori attraverso i socket
class Database: 
    def __init__(self):
        self.data = []
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
    
    def new_client(self) -> int:
        with self.l:    # prende il lock sulla lista
            n = len(self.data)
            self.data.append([])
        return n

    def update(self,id,data):
        self.data[id].extend(data)

def acceptation_thread(socket, database):
    while True:
        conn, addr = s.accept()
        threading.Thread(target=threaded_client, args=(conn, addr, database)).start()


def threaded_client(conn:socket.socket, addr, database: Database):
    id = database.new_client()
    print(f"Il client {addr} si è connesso con ID={id}")

    while True:
        data = conn.recv(4096)
        n = len(data)
        if n == 0:
            break
        print(f"ID={id} - Ricevuti {n} bytes")
        try:
            data_list = pickle.loads(data)
        except pickle.UnpicklingError:
            print("Dati corrotti")
            continue
        print(f"ID={id} - Lunghezza vettore: {len(data_list)}")
        database.update(id, data_list)

    print(f"Il client {addr} si è disconnesso")
    conn.close()

if __name__=="__main__":
    PORT = 3125
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        s.bind(("", PORT))
    except socket.error as e:
        print(e)

    s.listen()
    print(
        f"Server avviato su: {socket.gethostbyname(socket.gethostname())}:{PORT}")

    database = Database()
    acc_thread = threading.Thread(target=acceptation_thread, args=(s,database), daemon=True)
    acc_thread.start()
    while True:
        try:
            esc = input()
        except KeyboardInterrupt:
            exit()
        if esc!="":
            exit()

