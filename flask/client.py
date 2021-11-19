import threading
import socket

class Client(threading.Thread):

    def __init__(self, id:int, conn:socket.socket, addr:str, socketio) -> None:
        super().__init__()
        self.data : list[int] = []
        self.msg_queue : list[str] = []
        self.id_client = id
        self.file = None
        self.conn = conn
        self.addr = addr
        self.closed = False
        self.msg_queue_lock = threading.Lock()
        self.socketio = socketio
        print(f"Il client {self.addr} si è connesso con ID={self.id_client}")

    def send_msg(self, msg:str):
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
            
    def run(self):
        filename = ""
        acq_count = 0
        while True: #ciclo principale del thread del client

            #attesa comando start o close
            while not self.msg_queue and not self.closed:
                pass
            
            if self.closed:
                break
            filename = f"id{self.id_client}_acq{acq_count}.csv"
            #invio comando start al socket e creo il file
            self.file = open(filename, "w")
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
                    self.save_buffer_to_file()
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
                self.socketio.emit("data-from-id", {"id": self.id_client, "data": data_parsed})
                self.data.extend(data_parsed)
                if len(self.data) > 2048:
                    self.save_buffer_to_file()
            self.log(f"Salvataggio file {filename} in corso...")
            self.file.close()
            self.log(f"Salvataggio file {filename} completato")

        self.conn.close()
        self.log("Connessione chiusa")
