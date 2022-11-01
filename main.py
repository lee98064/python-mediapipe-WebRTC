import argparse
import asyncio
from concurrent.futures import process
import json
import logging
import os
import platform
import re
import ssl
import time
import json
from turtle import st

import cv2
from aiohttp import web, WSMsgType
from aiortc import (
    MediaStreamTrack,
    RTCDataChannel,
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack,
)
from aiortc.contrib.media import MediaPlayer, MediaRelay
from av import VideoFrame
from Services.ProcessImage import ProcessImage

ROOT = os.path.dirname(__file__)


relay = None
webcam = None

personal_pool = {}
room_pool = {}


async def index(request):
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    print(request.path)
    content = open(os.path.join(ROOT, "js/client.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)

    room = request.query.get('room')
    user_name = request.query.get('user_name')

    if room:
        await server(pc, offer, room, user_name)
    else:
        await server(pc, offer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


async def broadcast_msg(user_name, msg, room=""):

    if type(msg) == dict:
        msg = json.dumps(msg)

    # 如果不是聊天室，则单独返回
    if not room:
        ws = personal_pool[user_name]
        await ws.send_str(msg)
    # 如果是聊天室则广播
    else:
        users = room_pool[room]
        for name, ws in users.items():
            # if user_name != name:
            await ws.send_str(msg)


async def websocket_handler(request):
    # ws init
    ws = web.WebSocketResponse()

    # 等待用戶連線
    await ws.prepare(request)
    room = request.query.get('room')
    user_name = request.query.get('user_name')
    print("room", room)
    print("user_name", user_name)

    if room:
        if room in room_pool:
            room_pool[room][user_name] = ws
        else:
            room_pool[room] = {user_name: ws}

    else:
        if user_name in personal_pool:
            await ws.send_str("名字已有")
            print('websocket connection closed')
            return ws
        else:
            personal_pool[user_name] = ws

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
            else:
                await broadcast_msg(user_name, msg.data, room)
                # await ws.send_str(msg.data + '->/answer')

        elif msg.type == WSMsgType.ERROR:
            print('ws connection closed with exception %s' % ws.exception())

    # 斷開連結
    print('websocket connection closed')
    return ws

pcs = set()


async def server(pc, offer, room=None, user_name=None):
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("Connection state is %s" % pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        print("======= received track: ", track)
        if track.kind == "video":
            t = FaceSwapper(track, room, user_name)
            pc.addTrack(t)

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


class FaceSwapper(VideoStreamTrack):
    kind = "video"

    def __init__(self, track, room, user_name):
        super().__init__()
        self.track = track
        self.processImage = ProcessImage()
        self.room = room
        self.user_name = user_name
        # self.face_detector = cv2.CascadeClassifier(
        #     "./haarcascade_frontalface_alt.xml")
        # self.face = cv2.imread("./wu.png")

    async def recv(self):
        timestamp, video_timestamp_base = await self.next_timestamp()
        frame = await self.track.recv()
        frame = frame.to_ndarray(format="bgr24")
        frame = self.processImage.process_frame(frame)

        if self.room != None:
            await broadcast_msg(self.user_name, {
                "counter": self.processImage.counter,
                "stage": self.processImage.stage
            }, self.room)

        # s = time.time()
        # face_zones = self.face_detector.detectMultiScale(
        #     cv2.cvtColor(frame, code=cv2.COLOR_BGR2GRAY)
        # )
        # for x, y, w, h in face_zones:
        #     face = cv2.resize(self.face, dsize=(w, h))
        #     frame[y : y + h, x : x + w] = face
        frame = VideoFrame.from_ndarray(frame, format="bgr24")
        frame.pts = timestamp
        frame.time_base = video_timestamp_base
        return frame


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC webcam demo")
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host for HTTP server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port for HTTP server (default: 8080)"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.add_routes([
        web.get('/ws', websocket_handler),
        web.static("/js", os.path.join(ROOT, "js")),
        web.static("/css", os.path.join(ROOT, "css")),
        web.static("/img", os.path.join(ROOT, "img")),
        web.static("/vendor", os.path.join(ROOT, "vendor")),
    ])

    # app.router.add_get("/js/", javascript)
    app.router.add_post("/offer", offer)
    web.run_app(app, host=args.host, port=args.port)
