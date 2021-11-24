import threading
import socket
import time
import client_utils

class Client(threading.Thread):

    def __init__(self, id:int, conn:socket.socket, addr:str, socketio) -> None:
        super().__init__()
        self.is_alive = True
        self.data : list[int] = []
        self.msg_queue : list[str] = []
        self.id_client = id
        self.file = None
        self.conn = conn
        self.addr = addr
        self.closed = False
        self.acq_count = 0
        self.msg_queue_lock = threading.Lock()
        self.socketio = socketio

        print(f"Il client {self.addr} si è connesso con ID={self.id_client}")

        self.conn.settimeout(3)

    def send_msg(self, msg:bytearray):
        with self.msg_queue_lock:
            self.msg_queue.append(msg)

    def close(self):
        if not self.closed:
            self.closed = True
    
    def log(self, msg):
        print(f"ID={self.id_client} - {msg}")
    
    def save_buffer_to_file(self):
        self.file.write("\n".join(map(str, self.data))+"\n")
        self.data.clear()

    def ping(self) -> bool:
        try:
            self.conn.recv(128)
            return True
        except (socket.timeout, ConnectionResetError):
            self.socketio.emit("connection-lost", {"id" : self.id_client})
            return False

    def acq(self, msg):
        #ACQUISIZIONE
        filename = f"id{self.id_client}_acq{self.acq_count}.csv"
        #invio comando start al socket e creo il file
        self.file = open(filename, "w")
        self.acq_count += 1

        #ciclo di acquisizione
        count = 0  # contatore pacchetti

        self.conn.sendall(msg)
        while True:
            data = self.conn.recv(128)
            count += 1
            n = len(data)

            if n == 0:
                self.close()
                break
            elif n == 4 and "stop" in data.decode():
                self.log("Ricevuto stop")
                self.save_buffer_to_file()
                break
            self.log(f"Ricezione {count}: Ricevuti {n} bytes")
            print(data)
            try:
                data_list = list(data)
                data_parsed = []
                for i in range(0, n, 2):
                    data_parsed.append(
                        (data_list[i+1] << 8) + data_list[i])
            except Exception as e:
                print(e)
                self.log("Dati corrotti")
                continue
            self.log(f"Lunghezza vettore: {len(data_parsed)}")
            print(data_parsed)
            self.socketio.emit(
                "data-from-id", {"id": self.id_client, "data": data_parsed})
            self.data.extend(data_parsed)
            if len(self.data) > 2048:
                self.save_buffer_to_file()

        self.log(f"Salvataggio file {filename} in corso...")
        self.file.close()
        self.log(f"Salvataggio file {filename} completato")
        self.socketio.emit("acquisition-terminated", {"id": self.id_client})
            
    def run(self):
        now = time.time()
        while True: #ciclo principale del thread del client
            #attesa comando start o close
            while not self.msg_queue and not self.closed:
                if time.time() - now > 5:
                    now = time.time()
                    self.send_msg(bytearray([client_utils.PING]))

            if self.closed:
                break

            start = None
            with self.msg_queue_lock:
                if (self.msg_queue):
                    msg = self.msg_queue.pop(0)
                    if msg[0]==client_utils.START:
                        start = msg
                    elif msg[0] == client_utils.PING:
                        self.conn.sendall(msg)
                        if not self.ping():
                            break   #esce dal while principale e chiude il thread
                    else:
                        self.conn.sendall(msg)

            if start:
                self.acq(start)

        self.is_alive = False
        self.conn.close()
        self.log("Connessione chiusa")
