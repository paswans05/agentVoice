"""Telephony media, codec negotiation, G.711 PCMU/PCMA conversion, and jitter buffering."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import struct
import time

from app.providers.telephony.base import TelephonyMediaError

_ULAW_BIAS = 0x84
_ULAW_CLIP = 32635


def _linear_to_ulaw_sample(sample: int) -> int:
    sign = 0x80 if sample < 0 else 0
    if sample < 0:
        sample = -sample
    if sample > _ULAW_CLIP:
        sample = _ULAW_CLIP
    sample += _ULAW_BIAS
    exponent = 7
    mask = 0x4000
    while exponent > 0 and (sample & mask) == 0:
        exponent -= 1
        mask >>= 1
    mantissa = (sample >> (exponent + 3)) & 0x0F
    return (~(sign | (exponent << 4) | mantissa)) & 0xFF


def _ulaw_to_linear_sample(ulaw: int) -> int:
    ulaw = (~ulaw) & 0xFF
    sign = ulaw & 0x80
    exponent = (ulaw >> 4) & 0x07
    mantissa = ulaw & 0x0F
    sample = ((mantissa << 3) + _ULAW_BIAS) << exponent
    sample -= _ULAW_BIAS
    return -sample if sign else sample


def _linear_to_alaw_sample(sample: int) -> int:
    sign = 0x00 if sample >= 0 else 0x80
    if sample < 0:
        sample = -sample - 1 if sample > -32768 else 32767
    if sample >= 256:
        exponent = 7
        mask = 0x4000
        while exponent > 1 and (sample & mask) == 0:
            exponent -= 1
            mask >>= 1
        mantissa = (sample >> (exponent + 3)) & 0x0F
        alaw = sign | (exponent << 4) | mantissa
    else:
        alaw = sign | (sample >> 4)
    return alaw ^ 0x55


def _alaw_to_linear_sample(alaw: int) -> int:
    alaw ^= 0x55
    sign = alaw & 0x80
    exponent = (alaw & 0x70) >> 4
    mantissa = alaw & 0x0F
    if exponent == 0:
        sample = (mantissa << 4) + 8
    else:
        sample = ((mantissa << 4) + 0x108) << (exponent - 1)
    return -sample if sign else sample


_ULAW_DECODE_TABLE = [_ulaw_to_linear_sample(i) for i in range(256)]
_ALAW_DECODE_TABLE = [_alaw_to_linear_sample(i) for i in range(256)]


class AudioFrameBuffer:
    """Bounded jitter/frame buffer with packet-loss concealment (comfort silence)."""

    def __init__(self, max_frames: int = 50, frame_bytes: int = 320) -> None:
        self._frames: deque[bytes] = deque(maxlen=max_frames)
        self._frame_bytes = frame_bytes
        self.dropped_frames = 0
        self.concealed_packets = 0

    def push(self, frame: bytes) -> None:
        if len(self._frames) == self._frames.maxlen:
            self.dropped_frames += 1
        self._frames.append(frame)

    def pop_or_conceal(self) -> bytes:
        if not self._frames:
            self.concealed_packets += 1
            return b"\x00" * self._frame_bytes
        return self._frames.popleft()

    def clear(self) -> None:
        self._frames.clear()

    def __len__(self) -> int:
        return len(self._frames)


@dataclass(slots=True)
class MediaConversionResult:
    audio_bytes: bytes
    codec: str
    sample_rate: int
    conversion_latency_ms: float


class TelephonyMediaAdapter:
    """Handles codec negotiation, G.711 PCMU/PCMA <-> PCM16, and sample-rate conversion."""

    SUPPORTED_CODECS = ("PCMU", "PCMA", "L16", "OPUS")

    @classmethod
    def negotiate_codec(
        cls,
        provider_codecs: list[str],
        preferred_codecs: list[str],
    ) -> str:
        provider_norm = [c.strip().upper() for c in provider_codecs if c.strip()]
        for pref in preferred_codecs:
            p = pref.strip().upper()
            if p in provider_norm and p in cls.SUPPORTED_CODECS:
                return p
        for fallback in provider_norm:
            if fallback in cls.SUPPORTED_CODECS:
                return fallback
        raise TelephonyMediaError(
            f"No compatible audio codec between provider {provider_codecs} and preferred {preferred_codecs}."
        )

    @staticmethod
    def resample_pcm16(pcm_bytes: bytes, src_rate: int, dst_rate: int) -> bytes:
        if src_rate == dst_rate or not pcm_bytes:
            return pcm_bytes
        count = len(pcm_bytes) // 2
        if count == 0:
            return b""
        samples = struct.unpack(f"<{count}h", pcm_bytes[: count * 2])
        out_count = max(1, int(round(count * dst_rate / src_rate)))
        ratio = count / out_count
        out: list[int] = []
        for i in range(out_count):
            pos = i * ratio
            idx = int(pos)
            frac = pos - idx
            s0 = samples[min(idx, count - 1)]
            s1 = samples[min(idx + 1, count - 1)]
            val = int(round(s0 + (s1 - s0) * frac))
            out.append(max(-32768, min(32767, val)))
        return struct.pack(f"<{len(out)}h", *out)

    @classmethod
    def decode_to_pcm16_16k(cls, payload: bytes, codec: str, src_rate: int = 8000) -> MediaConversionResult:
        t0 = time.monotonic()
        c = codec.strip().upper()
        if c == "PCMU":
            samples = [_ULAW_DECODE_TABLE[b] for b in payload]
            pcm_src = struct.pack(f"<{len(samples)}h", *samples)
        elif c == "PCMA":
            samples = [_ALAW_DECODE_TABLE[b] for b in payload]
            pcm_src = struct.pack(f"<{len(samples)}h", *samples)
        elif c == "L16":
            pcm_src = payload
        else:
            raise TelephonyMediaError(f"Unsupported inbound codec '{codec}' for local decoding.")
        pcm_16k = cls.resample_pcm16(pcm_src, src_rate, 16000)
        return MediaConversionResult(
            audio_bytes=pcm_16k,
            codec="L16",
            sample_rate=16000,
            conversion_latency_ms=round((time.monotonic() - t0) * 1000, 3),
        )

    @classmethod
    def encode_from_pcm16(
        cls,
        pcm16_bytes: bytes,
        codec: str,
        *,
        src_rate: int = 16000,
        dst_rate: int = 8000,
    ) -> MediaConversionResult:
        t0 = time.monotonic()
        c = codec.strip().upper()
        pcm_dst = cls.resample_pcm16(pcm16_bytes, src_rate, dst_rate)
        count = len(pcm_dst) // 2
        samples = struct.unpack(f"<{count}h", pcm_dst[: count * 2]) if count else ()
        if c == "PCMU":
            out = bytes(_linear_to_ulaw_sample(s) for s in samples)
        elif c == "PCMA":
            out = bytes(_linear_to_alaw_sample(s) for s in samples)
        elif c == "L16":
            out = pcm_dst
        else:
            raise TelephonyMediaError(f"Unsupported outbound codec '{codec}'.")
        return MediaConversionResult(
            audio_bytes=out,
            codec=c,
            sample_rate=dst_rate,
            conversion_latency_ms=round((time.monotonic() - t0) * 1000, 3),
        )
