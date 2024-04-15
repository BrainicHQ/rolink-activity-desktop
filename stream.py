import requests
import websocket
import threading
import pyaudio
import numpy as np
import time

# Constants
AUDIO_SAMPLE_RATE_HIGH = 48000
RECEIVE_AUDIO_PREBUFFERING = 5
AUDIO_IDLE_TIMEOUT = 1.0  # Seconds

# Audio Playback States
AUDIO_STATE_IDLE = 0
AUDIO_STATE_BUFFERING = 1
AUDIO_STATE_PLAYING = 2

# Global Variables
audio_stream = None
audio_chunks = []
audio_playback_state = AUDIO_STATE_IDLE
playback_thread = None
proxy_handle = ""
isConnected = False


def connect():
    global isConnected
    """
    Connect to the EchoLink proxy server.
    """
    url = "https://webapp.echolink.org/ProxyServlet"
    data = {
        "remoteCallsign": "YO3KSR-L",
        "myName": "webapp.echolink.org",
        "proxyHandle": proxy_handle,
        "acceptingIncoming": "false",
        "method": "connect"
    }
    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "en-US,en;q=0.9,ro-US;q=0.8,ro;q=0.7",
        "cache-control": "no-cache",
        "content-type": "application/json; charset=UTF-8",
        "pragma": "no-cache",
        "sec-ch-ua": "\"Google Chrome\";v=\"123\", \"Not:A-Brand\";v=\"8\", \"Chromium\";v=\"123\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"macOS\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "x-requested-with": "XMLHttpRequest"
    }

    response = requests.post(url, json=data, headers=headers)

    # Handle the response
    if response.json().get("success") is True:
        try:
            response_data = response.json()
            print("Request was successful:", response_data)
            isConnected = True
            return response_data
        except ValueError:
            print("Response is not in JSON format.")
            isConnected = False
            return None
    else:
        print("Request failed:", response.json())
        return None


def on_message(ws, message):
    global audio_chunks, audio_playback_state
    data_type = message[0]
    if data_type == 1:  # Assuming SOCKET_DATA_TYPE_AUDIO == 1
        audio_data = np.frombuffer(message[2:], dtype=np.int16)
        audio_chunks.append(audio_data)
        manage_audio_playback()


def manage_audio_playback():
    global audio_playback_state, playback_thread
    if audio_playback_state == AUDIO_STATE_IDLE and audio_chunks:
        audio_playback_state = AUDIO_STATE_BUFFERING
    if audio_playback_state == AUDIO_STATE_BUFFERING and len(audio_chunks) > RECEIVE_AUDIO_PREBUFFERING:
        audio_playback_state = AUDIO_STATE_PLAYING
        if playback_thread is None or not playback_thread.is_alive():
            playback_thread = threading.Thread(target=play_audio)
            playback_thread.start()


def play_audio():
    global audio_chunks, audio_playback_state
    while audio_playback_state == AUDIO_STATE_PLAYING and audio_chunks:
        chunk = audio_chunks.pop(0)
        frames = (chunk / 32767.0).astype(np.float32).tobytes()
        audio_stream.write(frames)
    time.sleep(AUDIO_IDLE_TIMEOUT)
    audio_playback_state = AUDIO_STATE_IDLE
    print("Audio playback idle")


def setup_audio_playback():
    global audio_stream
    p = pyaudio.PyAudio()
    audio_stream = p.open(format=pyaudio.paFloat32,
                          channels=1,
                          rate=AUDIO_SAMPLE_RATE_HIGH,
                          output=True)


def start_websocket(url):
    ws = websocket.WebSocketApp(url,
                                on_message=on_message,
                                on_error=lambda ws, error: print("WebSocket error:", error),
                                on_close=lambda ws: print("### WebSocket Closed ###"),
                                on_open=lambda ws: print("WebSocket opened"))
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()


if __name__ == "__main__":
    connect()  # Connect to the EchoLink proxy
    if not isConnected:
        print("Failed to connect to the EchoLink proxy.")
        exit(1)
    setup_audio_playback()
    start_websocket("wss://rolink-live.silviu.workers.dev/")
    try:
        while True:  # Keep the main thread alive
            time.sleep(1)
    except KeyboardInterrupt:
        audio_stream.stop_stream()
        audio_stream.close()
        print("Program terminated")
