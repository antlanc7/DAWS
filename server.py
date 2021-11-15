#!/usr/bin/env python3

import pickle
import socket
import numpy as np
from scipy import signal
import threading

class Client(threading.Thread):

    def __init__(self, id:int, conn:socket.socket, addr:str) -> None:
        super().__init__()
        self.data : list[int] = []
        self.msg_queue : list[str] = []
        self.id_client = id
        self.file = None
        self.conn = conn
        self.addr = addr
        self.closed = False
        self.msg_queue_lock = threading.Lock()
        print(f"Il client {self.addr} si è connesso con ID={self.id_client}")

    def send_msg(self, msg:str):
        with self.msg_queue_lock:
            self.msg_queue.append(msg)

    def close(self):
        if not self.closed:
            self.closed = True
    
    def log(self, msg):
        print(f"ID={self.id_client} - {msg}")
            
    def run(self):
        
        acq_count = 0
        while True: #ciclo principale del thread del client

            #attesa comando start o close
            while not self.msg_queue and not self.closed:
                pass
            
            if self.closed:
                break

            #invio comando start al socket e creo il file
            self.file = open(f"{self.id_client}_{acq_count}.csv", "w")
            acq_count += 1

            with self.msg_queue_lock:
                while (self.msg_queue):
                    self.conn.sendall(self.msg_queue.pop(0).encode())

            #ciclo di acquisizione
            count = 0   #contatore pacchetti
            while True:
                data = self.conn.recv(128)
                count+=1
                n = len(data)
                
                if n == 0:
                    self.close()
                    break
                elif n == 4 and "stop" in data.decode():
                    self.log("Ricevuto stop")
                    break
                self.log(f"Ricezione {count}: Ricevuti {n} bytes")
                print(data)
                try:
                    data_list = list(data)
                    data_parsed = []
                    for i in range(0, n, 2):
                        data_parsed.append((data_list[i+1] << 8) + data_list[i])
                except Exception as e:
                    print(e)
                    self.log("Dati corrotti")
                    continue
                self.log(f"Lunghezza vettore: {len(data_parsed)}")
                print(data_parsed)
                self.data.extend(data_parsed)
                if len(self.data) > 2048:
                    self.file.write("\n".join(map(str, self.data))+"\n")
                    self.data.clear()
            self.log("Salvataggio file in corso...")
            self.file.close()
            self.log("Salvataggio completato")

        self.conn.close()
        self.log("Connessione chiusa")
        

#classe che raccoglie i dati ricevuti dai diversi sensori attraverso i socket
class Controller: 
    def __init__(self):
        self.clients : list[Client] = []
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
    
    def new_client(self,conn,addr):
        with self.l:
            id = len(self.clients)
            client = Client(id, conn, addr)
            self.clients.append(client)
            client.start()
    
    def start_all(self, acq_time:int):
        self.send_all(bytearray([1,acq_time]).decode())

    def send_all(self, msg:str):
        for client in self.clients:
            client.send_msg(msg)
        
    def close_all(self):
        for client in self.clients:
            client.close()
            client.join()
        self.clients.clear()


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
        elif cmd!="":   #esci scrivendo qualcosa a caso (no numeri)
            break
    controller.close_all()
    s.close()
    acc_thread.join()
