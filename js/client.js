var pc = null;
var localVideo = document.querySelector("video#localVideo");
var serverVideo = document.querySelector("video#serverVideo");

var room = generateRandomString(5);
var user_name = generateRandomString(5);

navigator.mediaDevices
  .getUserMedia({
    video: {
      height: 360,
      width: 480,
      frameRate: 10,
    },
  })
  .then((stream) => {
    localVideo.srcObject = stream;
    localVideo.addEventListener("loadedmetadata", () => {
      localVideo.play();
    });
  });

function negotiate() {
  return pc
    .createOffer()
    .then(function (offer) {
      return pc.setLocalDescription(offer);
    })
    .then(function () {
      // wait for ICE gathering to complete
      return new Promise(function (resolve) {
        if (pc.iceGatheringState === "complete") {
          resolve();
        } else {
          function checkState() {
            if (pc.iceGatheringState === "complete") {
              pc.removeEventListener("icegatheringstatechange", checkState);
              resolve();
            }
          }
          pc.addEventListener("icegatheringstatechange", checkState);
        }
      });
    })
    .then(function () {
      var offer = pc.localDescription;
      return fetch(`/offer?room=${room}&user_name=${user_name}`, {
        body: JSON.stringify({
          sdp: offer.sdp,
          type: offer.type,
        }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      });
    })
    .then(function (response) {
      return response.json();
    })
    .then(function (answer) {
      return pc.setRemoteDescription(answer);
    })
    .catch(function (e) {
      alert(e);
    });
}

function start() {
  var config = {
    sdpSemantics: "unified-plan",
    iceServers: [{ urls: ["stun:stun.l..com:19302"] }],
  };

  pc = new RTCPeerConnection(config);

  localVideo.srcObject.getVideoTracks().forEach((track) => {
    pc.addTrack(track);
  });
  pc.addEventListener("track", function (evt) {
    console.log("receive server video");
    if (evt.track.kind == "video") {
      serverVideo.srcObject = evt.streams[0];
    }
  });

  wsStart();
  document.getElementById("start").style.display = "none";
  negotiate();
  document.getElementById("stop").style.display = "inline-block";
}

function generateRandomString(num) {
  const characters =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let result1 = "";
  const charactersLength = characters.length;
  for (let i = 0; i < num; i++) {
    result1 += characters.charAt(Math.floor(Math.random() * charactersLength));
  }

  return result1;
}

function stop() {
  document.getElementById("stop").style.display = "none";
  document.getElementById("start").style.display = "inline-block";
  setTimeout(function () {
    pc.close();
  }, 500);
}

function wsStart() {
  let socket = new WebSocket(
    `ws://localhost:8080/ws?room=${room}&user_name=${user_name}`
  );

  socket.onopen = function (e) {
    console.log("[open] Connection established");
    // console.log("Sending to server");
    // socket.send("My name is John");
  };

  socket.onmessage = function (event) {
    const data = JSON.parse(event.data);
    document.querySelector("#information").innerHTML = `做了：${
      data.counter
    } 下，現在你的腳：${data.stage == "up" ? "抬起" : "放下"}`;
    // alert(`[message] Data received from server: ${event.data}`);
  };

  socket.onclose = function (event) {
    if (event.wasClean) {
      alert(
        `[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`
      );
    } else {
      // 例如服务器进程被杀死或网络中断
      // 在这种情况下，event.code 通常为 1006
      alert("[close] Connection died");
    }
  };

  socket.onerror = function (error) {
    alert(`[error] ${error.message}`);
  };
}