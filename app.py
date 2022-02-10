import asyncio, datetime, os

import flask
from flask import Flask, jsonify, render_template, request
from flask_socketio import send, SocketIO, join_room, leave_room
from deepgram import Deepgram


DEEPGRAM_API_KEY = os.environ.get('DEEPGRAM_API_KEY')
PATH_TO_FILE = 'you-can-stay-at-home.wav'

UPLOAD_DIRECTORY = "uploads"

if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# sio = socketio.AsyncServer()
# app = socketio.WSGIApp(sio, app)

socket_io = SocketIO(app)

dg_socket = None


def transcript_handler(data):
    print('transcript handler')
    if 'channel' in data:
        transcript = data['channel']['alternatives'][0]['transcript']
        print('received transcript:', transcript)
        socket_io.emit(transcript + ' has entered the room.', namespace='/test', to='my_room')
        # send(transcript, json=False, namespace='', to='my_room')
        print("sent")


async def connect_to_deepgram():
    global dg_socket

    if dg_socket:
        print('Socket to deepgram is already open')
        return

    # Initialize the Deepgram SDK
    dg_client = Deepgram(DEEPGRAM_API_KEY)

    # Create a websocket connection to Deepgram
    try:
        dg_socket = await dg_client.transcription.live({'punctuate': True})

        # Listen for the connection to close
        dg_socket.registerHandler(dg_socket.event.CLOSE, lambda c: print(f'Connection closed with code {c}.'))

        # Print incoming transcription objects
        dg_socket.registerHandler(dg_socket.event.TRANSCRIPT_RECEIVED, transcript_handler)

        # await process_audio(dg_socket)
    except Exception as e:
        print(f'Could not open socket: {e}')


async def process_audio(connection, filepath):
    print('processing audio')
    send('processing audio', json=False, namespace='', broadcast=True, include_self=True)
    if not filepath:
        filepath = PATH_TO_FILE

    # Open the file
    with open(filepath, 'rb') as audio:
        # Chunk up the audio to send
        CHUNK_SIZE_BYTES = 8192
        CHUNK_RATE_SEC = 0.001
        chunk = audio.read(CHUNK_SIZE_BYTES)
        while chunk:
            connection.send(chunk)
            await asyncio.sleep(CHUNK_RATE_SEC)
            chunk = audio.read(CHUNK_SIZE_BYTES)
            print('chunk')

    # Indicate that we've finished sending data
    print('finishing')
    await connection.finish()
    print('finished')


@socket_io.on('join', namespace='/test')
def on_join(data):
    print('on_join')
    username = data['username']
    room = data['room']
    join_room(room)
    send(username + ' has entered the room.', namespace='/test', to=room)


@socket_io.on('leave', namespace='/test')
def on_leave(data):
    print('on_leave')
    username = data['username']
    room = data['room']
    leave_room(room)
    send(username + ' has left the room.', to=room)


@socket_io.on('connect')
def handle_connection():
    print('client connected', flask.request.namespace, flask.request.sid)
    send("connected", json=False, namespace='', broadcast=True, include_self=True)


@socket_io.on('message', namespace='/test')
def handle_message(data):
    print('received message: ', data, flask.request.namespace, flask.request.sid)
    socket_io.send(f"You said: {data}", namespace='/test', to='my_room')
    # send(f"You said: {data}", json=False, namespace='', broadcast=True, include_self=True)

    # await connect_to_deepgram()
    # await process_audio(dg_socket, filepath)

    # loop = asyncio.get_event_loop()
    # try:
    #     loop.run_until_complete(process_audio(dg_socket))
    #     print('complete')
    # finally:
    #     loop.close()


@app.route("/")
async def index():
    return render_template('index.html')


@app.route("/audio")
async def audio():
    send("audio connected", json=False, namespace='', broadcast=True, include_self=True)
    return render_template('audio.html')


@app.route("/api/test", methods=['POST'])
async def test_api():
    print('test api')
    socket_io.send("test", namespace='/test', to='my_room')
    return jsonify({'sent': "processed"})


@app.route("/api/audio", methods=['POST'])
async def audio_api():
    file = request.files['audio']

    now = datetime.datetime.now().isoformat()
    filename = f"upload_{now}.webm"
    filepath = os.path.join(UPLOAD_DIRECTORY, filename)

    file.save(filepath)

    await connect_to_deepgram()
    await process_audio(dg_socket, filepath)

    send("processed", json=False, namespace='', broadcast=True, include_self=True)

    return jsonify({'filename': filename})


if __name__ == '__main__':
    socket_io.run(app, port=8000)
