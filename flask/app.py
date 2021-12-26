from flask import Flask, render_template
from flask_socketio import SocketIO

import socket
import threading
from controller import Controller

def acceptation_thread(s:socket.socket, controller:Controller):
    """ Thread to accept new M5 clients 

        Arguments:
            s          -- tcp/ip socket
            controller -- M5 clients controller
    """
    try:
        while True:
            conn, addr = s.accept()
            controller.new_client(conn, addr)
    except:
        pass
    finally:
        s.close()


app = Flask(__name__)
socketio = SocketIO(app)
controller = Controller(socketio)

@socketio.on("connect")
def browser_connection():
    """ When a browser client is connected it raise an envent to all browsers to update active clients """
    # connessione del client browser
    socketio.emit("clients-init", {"clients":[c.id_client for c in controller.get_active()]})


@socketio.on("M5-new-connection") # emitted by controller.py$Controller#new_client method
def m5_connection(id):
    """ When a new M5 client is connected it raise an envent to all browsers to add plot for this new client """
    # bisogna fare l'emit alla connessione del m5 nel controller
    print(f"\nM5Client connected. ID: {id}\n")

@socketio.on("start") # emitted by browser client
def start_acquisition(sec):
    """ start acquisition from all M5 for sec seconds """
    controller.start_all(int(sec))

@socketio.on("whereisit") # emitted by browser
def where_is_it(id):
    """ Turn on the id's M5 embedded LED"""
    controller.where_is_it(int(id))

@app.route("/")
def home():
    return render_template("index.html", clients = controller.clients)


if __name__ == '__main__':

    PORT = 3125
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        s.bind(("", PORT))
    except socket.error as e:
        print(e)

    s.listen()
    print(f"Server avviato sulla porta {PORT}")


    acc_thread = threading.Thread(target=acceptation_thread, args=(s,controller), daemon=True)
    acc_thread.start()

    socketio.run(app)

