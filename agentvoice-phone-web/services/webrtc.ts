"use client";

import { resolveApiBase } from "./api";

export interface WebRTCSessionHandles {
  peer: RTCPeerConnection;
  signalingWs: WebSocket;
  voiceWs: WebSocket;
  cleanup: () => void;
}

export async function startWebRTCVoiceConnection(params: {
  apiBase: string;
  deviceId: string;
  deviceToken: string;
  webrtcSessionId: string;
  voiceSessionId: string;
  stunUrls: string[];
  stream: MediaStream;
  onIceState: (state: string) => void;
  onTranscript: (speaker: "You" | "AI", text: string) => void;
  onAgentState: (state: string) => void;
  onAudioWav: (wavBuffer: ArrayBuffer) => void;
  onError: (msg: string) => void;
}): Promise<WebRTCSessionHandles> {
  const wsBase = resolveApiBase(params.apiBase).replace(/^http/, "ws");

  // 1. Authenticated WebRTC signaling WebSocket
  const signalingWs = new WebSocket(
    `${wsBase}/api/v1/webrtc/ws?device_id=${encodeURIComponent(params.deviceId)}&token=${encodeURIComponent(params.deviceToken)}`,
  );

  const peer = new RTCPeerConnection({
    iceServers: params.stunUrls.map((url) => ({ urls: url })),
  });

  for (const track of params.stream.getAudioTracks()) {
    peer.addTrack(track, params.stream);
  }

  peer.oniceconnectionstatechange = () => {
    const state = peer.iceConnectionState;
    params.onIceState(state);
    if (signalingWs.readyState === WebSocket.OPEN) {
      signalingWs.send(
        JSON.stringify({
          type: "ICE_STATE",
          session_id: params.webrtcSessionId,
          state,
        }),
      );
    }
  };

  peer.onicecandidate = (ev) => {
    if (ev.candidate && signalingWs.readyState === WebSocket.OPEN) {
      signalingWs.send(
        JSON.stringify({
          type: "ICE_CANDIDATE",
          session_id: params.webrtcSessionId,
          candidate: ev.candidate.toJSON(),
        }),
      );
    }
  };

  signalingWs.onopen = async () => {
    try {
      const offer = await peer.createOffer({ offerToReceiveAudio: true });
      await peer.setLocalDescription(offer);
      signalingWs.send(
        JSON.stringify({
          type: "OFFER",
          session_id: params.webrtcSessionId,
          sdp: offer.sdp,
        }),
      );
    } catch (err) {
      params.onError(err instanceof Error ? err.message : "WebRTC offer failed");
    }
  };

  // 2. Production VoiceConversationService WebSocket for STT -> LLM -> RAG -> TTS
  const voiceWs = new WebSocket(
    `${wsBase}/api/v1/voice/sessions/${encodeURIComponent(params.voiceSessionId)}/stream`,
  );
  voiceWs.binaryType = "arraybuffer";

  voiceWs.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
      params.onAudioWav(event.data);
      return;
    }
    try {
      const msg = JSON.parse(event.data as string);
      if (msg.type === "session.state") params.onAgentState(msg.state);
      else if (msg.type === "transcript.final") params.onTranscript("You", msg.text);
      else if (msg.type === "response.text") params.onTranscript("AI", msg.text);
      else if (msg.type === "error") params.onError(msg.message);
    } catch {
      // Ignore malformed frames
    }
  };

  // Stream PCM s16le 16kHz audio frames to VoiceConversationService
  const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const audioCtx = new AudioCtx({ sampleRate: 16000 });
  const source = audioCtx.createMediaStreamSource(params.stream);
  const processor = audioCtx.createScriptProcessor(4096, 1, 1);

  processor.onaudioprocess = (ev) => {
    if (voiceWs.readyState !== WebSocket.OPEN) return;
    const input = ev.inputBuffer.getChannelData(0);
    const pcm = new Int16Array(input.length);
    for (let i = 0; i < input.length; i += 1) {
      const s = Math.max(-1, Math.min(1, input[i]));
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    voiceWs.send(pcm.buffer);
  };

  source.connect(processor);
  processor.connect(audioCtx.destination);

  const cleanup = () => {
    try {
      processor.disconnect();
      source.disconnect();
      void audioCtx.close();
    } catch {
      // ignore
    }
    for (const track of params.stream.getTracks()) {
      track.stop();
    }
    peer.close();
    if (voiceWs.readyState === WebSocket.OPEN) {
      voiceWs.send(JSON.stringify({ type: "session.end" }));
    }
    voiceWs.close();
    signalingWs.close();
  };

  return { peer, signalingWs, voiceWs, cleanup };
}
