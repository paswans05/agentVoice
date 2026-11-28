/**
 * Lightweight RFC 7118 SIP-over-WebSocket + WebRTC client for Asterisk 23.
 * Supports REGISTER (Digest MD5), outgoing INVITE, incoming INVITE (answer/reject),
 * mute, hold (re-INVITE), DTMF (RTCDTMFSender / SIP INFO), and audio device selection.
 */

export type SipRegistrationState =
  | "unregistered"
  | "registering"
  | "registered"
  | "failed";

export type SipCallState =
  | "idle"
  | "calling"
  | "incoming"
  | "connected"
  | "held"
  | "ended";

export interface SipIncomingCall {
  callId: string;
  from: string;
  rawInvite: string;
}

export interface SipDialerCallbacks {
  onRegistrationChange?: (state: SipRegistrationState, detail?: string) => void;
  onCallStateChange?: (state: SipCallState, detail?: string) => void;
  onIncomingCall?: (incoming: SipIncomingCall) => void;
  onRemoteStream?: (stream: MediaStream) => void;
  onIceStateChange?: (iceState: RTCIceConnectionState) => void;
  onError?: (message: string) => void;
}

function md5Hex(input: string): string {
  const bytes = new TextEncoder().encode(input);
  const len = bytes.length;
  const paddedLen = (((len + 8) >> 6) + 1) << 6;
  const buf = new Uint8Array(paddedLen);
  buf.set(bytes);
  buf[len] = 0x80;
  const bitLen = len * 8;
  const view = new DataView(buf.buffer);
  view.setUint32(paddedLen - 8, bitLen >>> 0, true);
  view.setUint32(paddedLen - 4, Math.floor(bitLen / 0x100000000), true);

  let a0 = 0x67452301;
  let b0 = 0xefcdab89;
  let c0 = 0x98badcfe;
  let d0 = 0x10325476;

  const s = [
    7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22,
    5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20,
    4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23,
    6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21,
  ];
  const K = Array.from({ length: 64 }, (_, i) => Math.floor(Math.abs(Math.sin(i + 1)) * 0x100000000));

  for (let offset = 0; offset < paddedLen; offset += 64) {
    const M = Array.from({ length: 16 }, (_, j) => view.getUint32(offset + j * 4, true));
    let A = a0;
    let B = b0;
    let C = c0;
    let D = d0;
    for (let i = 0; i < 64; i++) {
      let F = 0;
      let g = 0;
      if (i < 16) {
        F = (B & C) | (~B & D);
        g = i;
      } else if (i < 32) {
        F = (D & B) | (~D & C);
        g = (5 * i + 1) % 16;
      } else if (i < 48) {
        F = B ^ C ^ D;
        g = (3 * i + 5) % 16;
      } else {
        F = C ^ (B | ~D);
        g = (7 * i) % 16;
      }
      const sum = (A + F + K[i] + M[g]) >>> 0;
      A = D;
      D = C;
      C = B;
      B = (B + (((sum << s[i]) | (sum >>> (32 - s[i]))) >>> 0)) >>> 0;
    }
    a0 = (a0 + A) >>> 0;
    b0 = (b0 + B) >>> 0;
    c0 = (c0 + C) >>> 0;
    d0 = (d0 + D) >>> 0;
  }

  return [a0, b0, c0, d0]
    .map((n) =>
      [n & 0xff, (n >> 8) & 0xff, (n >> 16) & 0xff, (n >> 24) & 0xff]
        .map((b) => b.toString(16).padStart(2, "0"))
        .join(""),
    )
    .join("");
}

function randomToken(len = 12): string {
  return Math.random().toString(36).slice(2, 2 + len);
}

function parseHeader(raw: string, name: string): string {
  const re = new RegExp(`^${name}:\\s*(.+)$`, "im");
  const m = raw.match(re);
  return m ? m[1].trim() : "";
}

function parseDigestParams(header: string): Record<string, string> {
  const out: Record<string, string> = {};
  const regex = /(\w+)="([^"]+)"/g;
  let match: RegExpExecArray | null = regex.exec(header);
  while (match) {
    out[match[1]] = match[2];
    match = regex.exec(header);
  }
  return out;
}

export class SipWebRTCClient {
  private ws: WebSocket | null = null;
  private pc: RTCPeerConnection | null = null;
  private localStream: MediaStream | null = null;
  private remoteStream: MediaStream | null = null;
  private callbacks: SipDialerCallbacks;

  private wsUrl = "";
  private domain = "";
  private extension = "";
  private password = "";
  private iceServers: RTCIceServer[] = [{ urls: "stun:stun.l.google.com:19302" }];
  private cseq = 1;
  private registerCallId = randomToken(16);
  private localTag = randomToken(10);
  private activeCallId = "";
  private remoteTag = "";
  private remoteTarget = "";
  private pendingIncoming: SipIncomingCall | null = null;
  private muted = false;
  private held = false;
  private keepaliveTimer: ReturnType<typeof setInterval> | null = null;

  constructor(callbacks: SipDialerCallbacks = {}) {
    this.callbacks = callbacks;
  }

  async connectAndRegister(opts: {
    wsUrl: string;
    domain: string;
    extension: string;
    password: string;
    iceServers?: RTCIceServer[];
  }): Promise<void> {
    this.disconnect();
    this.wsUrl = opts.wsUrl;
    this.domain = opts.domain;
    this.extension = opts.extension;
    this.password = opts.password;
    if (opts.iceServers?.length) {
      this.iceServers = opts.iceServers;
    }
    this.registerCallId = randomToken(16);
    this.callbacks.onRegistrationChange?.("registering", "Connecting to Asterisk WS...");

    const ws = new WebSocket(this.wsUrl, "sip");
    this.ws = ws;

    ws.onopen = () => {
      this.sendRegister();
      this.keepaliveTimer = setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.sendRegister();
        }
      }, 50_000);
    };

    ws.onerror = () => {
      this.callbacks.onRegistrationChange?.("failed", "WebSocket connection failed.");
      this.callbacks.onError?.(`Unable to reach Asterisk WebSocket at ${this.wsUrl}`);
    };

    ws.onclose = () => {
      if (this.keepaliveTimer) {
        clearInterval(this.keepaliveTimer);
        this.keepaliveTimer = null;
      }
      this.callbacks.onRegistrationChange?.("unregistered", "Disconnected");
    };

    ws.onmessage = (ev) => {
      if (typeof ev.data === "string") {
        void this.handleSipMessage(ev.data);
      }
    };
  }

  disconnect(): void {
    this.cleanupCallMedia();
    if (this.keepaliveTimer) {
      clearInterval(this.keepaliveTimer);
      this.keepaliveTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.callbacks.onRegistrationChange?.("unregistered");
  }

  private sendRaw(msg: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(msg);
    }
  }

  private buildDigestAuth(method: string, uri: string, challenge: string): string {
    const p = parseDigestParams(challenge);
    const realm = p.realm || this.domain;
    const nonce = p.nonce || "";
    const ha1 = md5Hex(`${this.extension}:${realm}:${this.password}`);
    const ha2 = md5Hex(`${method}:${uri}`);
    const response = p.qop
      ? md5Hex(`${ha1}:${nonce}:00000001:cnonce1:auth:${ha2}`)
      : md5Hex(`${ha1}:${nonce}:${ha2}`);
    return (
      `Digest username="${this.extension}", realm="${realm}", nonce="${nonce}", ` +
      `uri="${uri}", response="${response}", algorithm=MD5` +
      (p.qop ? `, qop=auth, nc=00000001, cnonce="cnonce1"` : "")
    );
  }

  private sendRegister(authHeader?: string): void {
    const uri = `sip:${this.domain}`;
    const branch = `z9hG4bK${randomToken(10)}`;
    const lines = [
      `REGISTER ${uri} SIP/2.0`,
      `Via: SIP/2.0/WSS ${this.domain};branch=${branch}`,
      `Max-Forwards: 70`,
      `To: <sip:${this.extension}@${this.domain}>`,
      `From: <sip:${this.extension}@${this.domain}>;tag=${this.localTag}`,
      `Call-ID: ${this.registerCallId}`,
      `CSeq: ${this.cseq++} REGISTER`,
      `Contact: <sip:${this.extension}@${this.domain};transport=ws>;expires=120`,
      ...(authHeader ? [`Authorization: ${authHeader}`] : []),
      `Content-Length: 0`,
      "",
      "",
    ];
    this.sendRaw(lines.join("\r\n"));
  }

  private async preparePeerConnection(inputDeviceId?: string): Promise<RTCPeerConnection> {
    this.cleanupCallMedia();
    const pc = new RTCPeerConnection({ iceServers: this.iceServers });
    this.pc = pc;
    this.remoteStream = new MediaStream();

    pc.ontrack = (ev) => {
      ev.streams[0]?.getTracks().forEach((t) => this.remoteStream?.addTrack(t));
      if (this.remoteStream) {
        this.callbacks.onRemoteStream?.(this.remoteStream);
      }
    };

    pc.oniceconnectionstatechange = () => {
      this.callbacks.onIceStateChange?.(pc.iceConnectionState);
    };

    this.localStream = await navigator.mediaDevices.getUserMedia({
      audio: inputDeviceId ? { deviceId: { exact: inputDeviceId } } : true,
      video: false,
    });
    this.localStream.getTracks().forEach((track) => {
      if (this.localStream) {
        pc.addTrack(track, this.localStream);
      }
    });
    return pc;
  }

  private async waitForIceComplete(pc: RTCPeerConnection): Promise<void> {
    if (pc.iceGatheringState === "complete") return;
    await new Promise<void>((resolve) => {
      const timer = setTimeout(resolve, 1500);
      pc.onicegatheringstatechange = () => {
        if (pc.iceGatheringState === "complete") {
          clearTimeout(timer);
          resolve();
        }
      };
    });
  }

  async call(targetExtension: string, inputDeviceId?: string): Promise<void> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error("Register your WebRTC extension before calling.");
    }
    this.activeCallId = randomToken(16);
    this.remoteTarget = targetExtension;
    this.held = false;
    this.muted = false;
    this.callbacks.onCallStateChange?.("calling", `Dialing ${targetExtension}...`);

    const pc = await this.preparePeerConnection(inputDeviceId);
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    await this.waitForIceComplete(pc);
    const sdp = pc.localDescription?.sdp || offer.sdp || "";
    this.sendInvite(targetExtension, sdp);
  }

  private sendInvite(target: string, sdp: string, authHeader?: string): void {
    const uri = `sip:${target}@${this.domain}`;
    const branch = `z9hG4bK${randomToken(10)}`;
    const lines = [
      `INVITE ${uri} SIP/2.0`,
      `Via: SIP/2.0/WSS ${this.domain};branch=${branch}`,
      `Max-Forwards: 70`,
      `To: <${uri}>`,
      `From: <sip:${this.extension}@${this.domain}>;tag=${this.localTag}`,
      `Call-ID: ${this.activeCallId}`,
      `CSeq: ${this.cseq++} INVITE`,
      `Contact: <sip:${this.extension}@${this.domain};transport=ws>`,
      ...(authHeader ? [`Authorization: ${authHeader}`] : []),
      `Content-Type: application/sdp`,
      `Content-Length: ${sdp.length}`,
      "",
      sdp,
    ];
    this.sendRaw(lines.join("\r\n"));
  }

  async answerIncoming(inputDeviceId?: string): Promise<void> {
    const inc = this.pendingIncoming;
    if (!inc) return;
    const raw = inc.rawInvite;
    const bodyIdx = raw.indexOf("\r\n\r\n");
    const remoteSdp = bodyIdx >= 0 ? raw.slice(bodyIdx + 4) : "";

    const pc = await this.preparePeerConnection(inputDeviceId);
    await pc.setRemoteDescription({ type: "offer", sdp: remoteSdp });
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    await this.waitForIceComplete(pc);

    const sdp = pc.localDescription?.sdp || answer.sdp || "";
    const via = parseHeader(raw, "Via");
    const from = parseHeader(raw, "From");
    const to = parseHeader(raw, "To");
    const cseq = parseHeader(raw, "CSeq");
    const lines = [
      `SIP/2.0 200 OK`,
      `Via: ${via}`,
      `From: ${from}`,
      `To: ${to};tag=${this.localTag}`,
      `Call-ID: ${inc.callId}`,
      `CSeq: ${cseq}`,
      `Contact: <sip:${this.extension}@${this.domain};transport=ws>`,
      `Content-Type: application/sdp`,
      `Content-Length: ${sdp.length}`,
      "",
      sdp,
    ];
    this.sendRaw(lines.join("\r\n"));
    this.activeCallId = inc.callId;
    this.pendingIncoming = null;
    this.callbacks.onCallStateChange?.("connected", `Connected with ${inc.from}`);
  }

  rejectIncoming(): void {
    const inc = this.pendingIncoming;
    if (!inc) return;
    const raw = inc.rawInvite;
    const lines = [
      `SIP/2.0 486 Busy Here`,
      `Via: ${parseHeader(raw, "Via")}`,
      `From: ${parseHeader(raw, "From")}`,
      `To: ${parseHeader(raw, "To")};tag=${this.localTag}`,
      `Call-ID: ${inc.callId}`,
      `CSeq: ${parseHeader(raw, "CSeq")}`,
      `Content-Length: 0`,
      "",
      "",
    ];
    this.sendRaw(lines.join("\r\n"));
    this.pendingIncoming = null;
    this.callbacks.onCallStateChange?.("idle");
  }

  hangup(): void {
    if (this.activeCallId && this.remoteTarget) {
      const uri = `sip:${this.remoteTarget}@${this.domain}`;
      const branch = `z9hG4bK${randomToken(10)}`;
      const lines = [
        `BYE ${uri} SIP/2.0`,
        `Via: SIP/2.0/WSS ${this.domain};branch=${branch}`,
        `Max-Forwards: 70`,
        `To: <${uri}>${this.remoteTag ? `;tag=${this.remoteTag}` : ""}`,
        `From: <sip:${this.extension}@${this.domain}>;tag=${this.localTag}`,
        `Call-ID: ${this.activeCallId}`,
        `CSeq: ${this.cseq++} BYE`,
        `Content-Length: 0`,
        "",
        "",
      ];
      this.sendRaw(lines.join("\r\n"));
    }
    this.cleanupCallMedia();
    this.activeCallId = "";
    this.callbacks.onCallStateChange?.("ended");
  }

  setMuted(mute: boolean): boolean {
    this.muted = mute;
    this.localStream?.getAudioTracks().forEach((t) => {
      t.enabled = !mute;
    });
    return this.muted;
  }

  async setHold(hold: boolean): Promise<boolean> {
    this.held = hold;
    this.localStream?.getAudioTracks().forEach((t) => {
      t.enabled = !hold && !this.muted;
    });
    if (this.pc?.localDescription?.sdp && this.remoteTarget && this.activeCallId) {
      const updatedSdp = this.pc.localDescription.sdp.replace(
        /a=(sendrecv|sendonly|recvonly|inactive)/g,
        hold ? "a=sendonly" : "a=sendrecv",
      );
      this.sendInvite(this.remoteTarget, updatedSdp);
    }
    this.callbacks.onCallStateChange?.(hold ? "held" : "connected");
    return this.held;
  }

  sendDtmf(digit: string): void {
    const sender = this.pc?.getSenders().find((s) => s.track?.kind === "audio");
    if (sender?.dtmf && sender.dtmf.canInsertDTMF) {
      sender.dtmf.insertDTMF(digit, 120, 70);
      return;
    }
    if (this.activeCallId && this.remoteTarget) {
      const uri = `sip:${this.remoteTarget}@${this.domain}`;
      const body = `Signal=${digit}\r\nDuration=120\r\n`;
      const lines = [
        `INFO ${uri} SIP/2.0`,
        `Via: SIP/2.0/WSS ${this.domain};branch=z9hG4bK${randomToken(10)}`,
        `Max-Forwards: 70`,
        `To: <${uri}>`,
        `From: <sip:${this.extension}@${this.domain}>;tag=${this.localTag}`,
        `Call-ID: ${this.activeCallId}`,
        `CSeq: ${this.cseq++} INFO`,
        `Content-Type: application/dtmf-relay`,
        `Content-Length: ${body.length}`,
        "",
        body,
      ];
      this.sendRaw(lines.join("\r\n"));
    }
  }

  private cleanupCallMedia(): void {
    this.localStream?.getTracks().forEach((t) => t.stop());
    this.localStream = null;
    if (this.pc) {
      this.pc.close();
      this.pc = null;
    }
    this.remoteStream = null;
  }

  private async handleSipMessage(raw: string): Promise<void> {
    const firstLine = raw.split("\r\n")[0] || "";
    const cseq = parseHeader(raw, "CSeq");
    const challenge = parseHeader(raw, "WWW-Authenticate") || parseHeader(raw, "Proxy-Authenticate");

    if (firstLine.startsWith("SIP/2.0 401") || firstLine.startsWith("SIP/2.0 407")) {
      if (cseq.includes("REGISTER") && challenge) {
        this.sendRegister(this.buildDigestAuth("REGISTER", `sip:${this.domain}`, challenge));
      } else if (cseq.includes("INVITE") && challenge && this.pc?.localDescription?.sdp) {
        const uri = `sip:${this.remoteTarget}@${this.domain}`;
        this.sendInvite(
          this.remoteTarget,
          this.pc.localDescription.sdp,
          this.buildDigestAuth("INVITE", uri, challenge),
        );
      }
      return;
    }

    if (firstLine.startsWith("SIP/2.0 200") && cseq.includes("REGISTER")) {
      this.callbacks.onRegistrationChange?.("registered", `Registered as ${this.extension}`);
      return;
    }

    if ((firstLine.startsWith("SIP/2.0 180") || firstLine.startsWith("SIP/2.0 183")) && cseq.includes("INVITE")) {
      this.callbacks.onCallStateChange?.("calling", "Ringing...");
      return;
    }

    if (firstLine.startsWith("SIP/2.0 200") && cseq.includes("INVITE")) {
      const bodyIdx = raw.indexOf("\r\n\r\n");
      const remoteSdp = bodyIdx >= 0 ? raw.slice(bodyIdx + 4) : "";
      if (this.pc && remoteSdp) {
        await this.pc.setRemoteDescription({ type: "answer", sdp: remoteSdp });
      }
      const uri = `sip:${this.remoteTarget}@${this.domain}`;
      this.sendRaw(
        [
          `ACK ${uri} SIP/2.0`,
          `Via: SIP/2.0/WSS ${this.domain};branch=z9hG4bK${randomToken(10)}`,
          `Max-Forwards: 70`,
          `To: ${parseHeader(raw, "To")}`,
          `From: ${parseHeader(raw, "From")}`,
          `Call-ID: ${this.activeCallId}`,
          `CSeq: ${cseq.replace("INVITE", "ACK")}`,
          `Content-Length: 0`,
          "",
          "",
        ].join("\r\n"),
      );
      this.callbacks.onCallStateChange?.("connected", `Connected to ${this.remoteTarget}`);
      return;
    }

    if (firstLine.startsWith("INVITE ")) {
      const callId = parseHeader(raw, "Call-ID");
      const from = parseHeader(raw, "From");
      this.pendingIncoming = { callId, from, rawInvite: raw };
      this.callbacks.onIncomingCall?.(this.pendingIncoming);
      this.callbacks.onCallStateChange?.("incoming", `Incoming call from ${from}`);
      return;
    }

    if (firstLine.startsWith("BYE ")) {
      this.sendRaw(
        [
          `SIP/2.0 200 OK`,
          `Via: ${parseHeader(raw, "Via")}`,
          `From: ${parseHeader(raw, "From")}`,
          `To: ${parseHeader(raw, "To")}`,
          `Call-ID: ${parseHeader(raw, "Call-ID")}`,
          `CSeq: ${cseq}`,
          `Content-Length: 0`,
          "",
          "",
        ].join("\r\n"),
      );
      this.cleanupCallMedia();
      this.activeCallId = "";
      this.callbacks.onCallStateChange?.("ended", "Remote party hung up");
    }
  }
}
