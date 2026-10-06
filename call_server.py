"""
SkillSwap Campus - WebRTC signaling server

Run separately from Streamlit:

    uvicorn call_server:app --host 0.0.0.0 --port 8000

For production, serve this through HTTPS/WSS and configure
CALL_SERVER_URL in config.py accordingly.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from collections import defaultdict
import json


app = FastAPI(title="SkillSwap Campus Call Server")


rooms = defaultdict(set)


CALL_PAGE = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SkillSwap Campus Call</title>
    <style>
        body {
            margin: 0;
            background: #071a33;
            color: white;
            font-family: Arial, sans-serif;
        }

        .top {
            padding: 18px;
            text-align: center;
        }

        .videos {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 14px;
            padding: 14px;
        }

        video {
            width: 100%;
            min-height: 260px;
            background: #020817;
            border-radius: 14px;
            object-fit: cover;
        }

        .controls {
            display: flex;
            justify-content: center;
            gap: 10px;
            padding: 18px;
            flex-wrap: wrap;
        }

        button {
            border: 0;
            border-radius: 10px;
            padding: 12px 18px;
            cursor: pointer;
            font-weight: bold;
        }

        .danger {
            background: #b42318;
            color: white;
        }

        #status {
            text-align: center;
            opacity: .85;
            padding-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="top">
        <h2 id="title">SkillSwap Campus Call</h2>
        <div id="status">Connecting...</div>
    </div>

    <div class="videos">
        <div>
            <h3>You</h3>
            <video id="localVideo" autoplay muted playsinline></video>
        </div>

        <div>
            <h3>Other student</h3>
            <video id="remoteVideo" autoplay playsinline></video>
        </div>
    </div>

    <div class="controls">
        <button id="muteBtn">🎙️ Mute</button>
        <button id="cameraBtn">📷 Camera Off</button>
        <button class="danger" id="endBtn">☎ End Call</button>
    </div>

<script>
const pathParts = window.location.pathname.split("/");
const roomId = decodeURIComponent(pathParts[pathParts.length - 1]);

const params = new URLSearchParams(window.location.search);
const mode = params.get("mode") === "video" ? "video" : "audio";

document.getElementById("title").textContent =
    mode === "video"
        ? "📹 SkillSwap Video Call"
        : "📞 SkillSwap Voice Call";

const localVideo = document.getElementById("localVideo");
const remoteVideo = document.getElementById("remoteVideo");
const statusBox = document.getElementById("status");

if (mode === "audio") {
    localVideo.style.display = "none";
    remoteVideo.style.display = "none";
}

let localStream = null;
let peer = null;
let socket = null;
let isCaller = false;

const configuration = {
    iceServers: [
        { urls: "stun:stun.l.google.com:19302" }
    ]
};

function setStatus(text) {
    statusBox.textContent = text;
}

async function start() {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({
            audio: true,
            video: mode === "video"
        });

        if (mode === "video") {
            localVideo.srcObject = localStream;
        }

        const protocol =
            window.location.protocol === "https:" ? "wss:" : "ws:";

        socket = new WebSocket(
            protocol +
            "//" +
            window.location.host +
            "/ws/" +
            encodeURIComponent(roomId)
        );

        socket.onopen = () => {
            setStatus("Waiting for the other student...");
            socket.send(JSON.stringify({
                type: "join"
            }));
        };

        socket.onmessage = async (event) => {
            const message = JSON.parse(event.data);

            if (message.type === "ready") {
                if (message.count === 1) {
                    isCaller = true;
                    setStatus("Waiting for the other student...");
                } else {
                    setStatus("Connecting...");
                }
                return;
            }

            if (message.type === "peer-joined") {
                if (isCaller) {
                    await createOffer();
                }
                return;
            }

            if (message.type === "offer") {
                await ensurePeer();

                await peer.setRemoteDescription(
                    new RTCSessionDescription(message.offer)
                );

                const answer = await peer.createAnswer();

                await peer.setLocalDescription(answer);

                socket.send(JSON.stringify({
                    type: "answer",
                    answer: peer.localDescription
                }));

                setStatus("Call connected");
                return;
            }

            if (message.type === "answer") {
                await peer.setRemoteDescription(
                    new RTCSessionDescription(message.answer)
                );

                setStatus("Call connected");
                return;
            }

            if (message.type === "candidate") {
                if (message.candidate) {
                    try {
                        await peer.addIceCandidate(
                            new RTCIceCandidate(message.candidate)
                        );
                    } catch (error) {
                        console.warn(error);
                    }
                }
                return;
            }

            if (message.type === "peer-left") {
                setStatus("The other student left the call.");
                if (peer) {
                    peer.close();
                    peer = null;
                }
            }
        };

        socket.onclose = () => {
            setStatus("Call connection closed.");
        };

    } catch (error) {
        console.error(error);
        setStatus(
            "Microphone/camera permission was denied or unavailable."
        );
    }
}

async function ensurePeer() {
    if (peer) {
        return peer;
    }

    peer = new RTCPeerConnection(configuration);

    for (const track of localStream.getTracks()) {
        peer.addTrack(track, localStream);
    }

    peer.ontrack = (event) => {
        if (event.streams && event.streams[0]) {
            remoteVideo.srcObject = event.streams[0];
        }
    };

    peer.onicecandidate = (event) => {
        if (event.candidate && socket) {
            socket.send(JSON.stringify({
                type: "candidate",
                candidate: event.candidate
            }));
        }
    };

    peer.onconnectionstatechange = () => {
        if (
            peer.connectionState === "connected"
        ) {
            setStatus("Call connected");
        }

        if (
            peer.connectionState === "failed"
            || peer.connectionState === "disconnected"
        ) {
            setStatus("Call connection interrupted.");
        }
    };

    return peer;
}

async function createOffer() {
    await ensurePeer();

    const offer = await peer.createOffer();

    await peer.setLocalDescription(offer);

    socket.send(JSON.stringify({
        type: "offer",
        offer: peer.localDescription
    }));
}

document.getElementById("muteBtn").onclick = () => {
    if (!localStream) return;

    const track = localStream.getAudioTracks()[0];

    if (!track) return;

    track.enabled = !track.enabled;

    document.getElementById("muteBtn").textContent =
        track.enabled ? "🎙️ Mute" : "🔇 Unmute";
};

document.getElementById("cameraBtn").onclick = () => {
    if (!localStream || mode !== "video") return;

    const track = localStream.getVideoTracks()[0];

    if (!track) return;

    track.enabled = !track.enabled;

    document.getElementById("cameraBtn").textContent =
        track.enabled ? "📷 Camera Off" : "📷 Camera On";
};

document.getElementById("endBtn").onclick = () => {
    if (socket) {
        socket.send(JSON.stringify({
            type: "leave"
        }));
        socket.close();
    }

    if (peer) {
        peer.close();
    }

    if (localStream) {
        localStream.getTracks().forEach(
            track => track.stop()
        );
    }

    window.close();

    setStatus("Call ended.");
};

window.addEventListener("beforeunload", () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: "leave"
        }));
    }

    if (localStream) {
        localStream.getTracks().forEach(
            track => track.stop()
        );
    }
});

start();
</script>
</body>
</html>
"""


@app.get("/")
async def root():
    return {
        "service": "SkillSwap Campus Call Server",
        "status": "running"
    }


@app.get("/call/{room_id}", response_class=HTMLResponse)
async def call_page(room_id: str):
    return HTMLResponse(CALL_PAGE)


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()

    room = rooms[room_id]
    room.add(websocket)

    try:
        await websocket.send_text(
            json.dumps({
                "type": "ready",
                "count": len(room)
            })
        )

        for client in list(room):
            if client is not websocket:
                try:
                    await client.send_text(
                        json.dumps({
                            "type": "peer-joined"
                        })
                    )
                except Exception:
                    pass

        while True:
            raw = await websocket.receive_text()

            for client in list(room):
                if client is websocket:
                    continue

                try:
                    await client.send_text(raw)
                except Exception:
                    room.discard(client)

    except WebSocketDisconnect:
        pass

    finally:
        room.discard(websocket)

        for client in list(room):
            try:
                await client.send_text(
                    json.dumps({
                        "type": "peer-left"
                    })
                )
            except Exception:
                room.discard(client)

        if not room:
            rooms.pop(room_id, None)
