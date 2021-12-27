import numpy as np
from scipy import signal
import threading
from client import Client
import client_utils

from flask_socketio import emit


#classe che raccoglie i dati ricevuti dai diversi sensori attraverso i socket
class Controller:
    """ M5 clients controller Class """

    def __init__(self,socketio):
        """ args:
                socketio -- SocketIO to raise and listen for events
        """
        self.clients : list[Client] = []
        self.l = threading.Lock()
        self.socketio = socketio
        self.ids = 0

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
    
    def new_client(self, conn, addr):
        """ Handles new M5 client connection """
        with self.l: # semaphor wait
            # id = len(self.clients)
            client = Client(self.ids, conn, addr, self.socketio)
            self.clients.append(client)
            self.socketio.emit("M5-new-connection", {"id": str(self.ids)})
            self.ids += 1
            client.start()
    
    def start_all(self, acq_time:int):
        """ Puts start command in all clients commands queue 
        
        args:
            acq_time -- time of acquisition
        """
        self.send_all(bytearray([client_utils.START ,acq_time]))

    def send_all(self, msg:str):
        """ Send a message to all clients trough their message queues 
        
        args:
            msg -- command to be sent
        """
        for client in self.clients:
            client.send_msg(msg)
        
    def close_all(self):
        """ Close all M5 clients connection and wait their threads to stop """
        for client in self.clients:
            client.close()
            client.join()
        self.clients.clear()

    def get_active(self):
        """ Update and returns active M5 clients"""
        self.clients = [c for c in self.clients if c.is_alive]
        return self.clients
    
    def where_is_it(self, id : int):
        """ Puts WHEREISIT command in commands queue of the client with id = id
        
        args:
            id -- client's id
        """
        for c in self.clients:
            if c.id_client==id:
                c.send_msg(bytearray([client_utils.WHEREISIT]))
                break
