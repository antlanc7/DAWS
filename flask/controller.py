import numpy as np
from scipy import signal
import threading
from client import Client

from flask_socketio import emit


#classe che raccoglie i dati ricevuti dai diversi sensori attraverso i socket
class Controller: 
    def __init__(self,socketio):
        self.clients : list[Client] = []
        self.l = threading.Lock()
        self.socketio = socketio

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
            client = Client(id, conn, addr, self.socketio)
            self.clients.append(client)
            self.socketio.emit("M5-new-connection", {"id": str(id)})
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