import asyncio, datetime, os, socketio

import flask
from flask import Flask, jsonify, render_template, request
from flask_socketio import emit, send, SocketIO
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
    if 'channel' in data:
        transcript = data['channel']['alternatives'][0]['transcript']
        print('received transcript:', transcript)
        send(transcript, json=False, namespace='', broadcast=True, include_self=True)
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


async def process_audio(connection):
    print('processing audio')
    # Open the file
    with open(PATH_TO_FILE, 'rb') as audio:
        # Chunk up the audio to send
        CHUNK_SIZE_BYTES = 8192
        CHUNK_RATE_SEC = 0.001
        chunk = audio.read(CHUNK_SIZE_BYTES)
        while chunk:
            connection.send(chunk)
            await asyncio.sleep(CHUNK_RATE_SEC)
            chunk = audio.read(CHUNK_SIZE_BYTES)
            # print('chunk')

    # Indicate that we've finished sending data
    print('finishing')
    await connection.finish()
    print('finished')


# @sio.on('connect')
# def connect(sid, environ):
#     print("connected: ", sid)
# 
# 
# @sio.on('message')
# async def message(sid, data):
#     print("message ", data)
#     # await asyncio.sleep(1 * random.random())
#     # print('waited', data)
# 
# 
# @sio.on('disconnect')
# def disconnect(sid):
#     print('disconnect ', sid)


@socket_io.on('connect')
def handle_connection():
    print('client connected', flask.request.namespace, flask.request.sid)


@socket_io.on('message')
def handle_message(data):
    print('received message: ', data, flask.request.namespace, flask.request.sid)
    send(f"You said: {data}")
    
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
    return render_template('audio.html')


@app.route("/api/audio", methods=['POST'])
async def audio_api():
    file = request.files['audio']

    now = datetime.datetime.now().isoformat()
    filename = f"upload_{now}.webm"

    file.save(os.path.join(UPLOAD_DIRECTORY, filename))

    # await connect_to_deepgram()
    # await process_audio(dg_socket)
    return jsonify({'filename': filename})


if __name__ == '__main__':
    socket_io.run(app, port=8000)
