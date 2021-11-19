from flask import Flask, render_template
from flask_socketio import SocketIO

import socket
import threading
from controller import Controller

controller = None

def acceptation_thread(s:socket.socket, controller:Controller):
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

@socketio.on("connect")
def browser_connection():
    # connessione del client browser
    print("ciao")

@socketio.on("M5-new-connection")
def m5_connection(id):
    # bisogna fare l'emit alla connessione del m5 nel controller
    print(f"\nM5Client connected. ID: {id}\n")


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

    controller = Controller(socketio)
    acc_thread = threading.Thread(target=acceptation_thread, args=(s,controller), daemon=True)
    acc_thread.start()

    socketio.run(app)
