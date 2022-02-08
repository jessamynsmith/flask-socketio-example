from flask import Flask, render_template
from flask_socketio import send, SocketIO


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socket_io = SocketIO(app)


@socket_io.on('connect')
def handle_connection(data):
    print('client connected: ', data)


@socket_io.on('message')
def handle_message(data):
    print('received message: ', data)
    send(f"You said: {data}")


@app.route("/")
def hello_world():
    return render_template('index.html')


if __name__ == '__main__':
    socket_io.run(app)
