"""
TTS narration — best-effort text→speech synthesis for lesson narration.

Item #8. Tries available providers in order: edge-tts (free MS API, online),
pyttsx3 (offline, OS native), then a silent fallback that lets the pipeline
continue without audio.

Enabled by setting LUMEN_TTS_ENABLED=1 in the environment. Default: off, so
existing renders are unchanged and tests don't need network access.

Public surface:
    synthesize(text, out_path) -> bool
        Write a WAV/MP3 of ``text`` to ``out_path``. Returns True if real
        audio was written, False if a silent placeholder was written (caller
        can still mux it, just without sound). Never raises.

    mux_audio_into_video(video_path, audio_path, out_path) -> bool
        Use ffmpeg to merge ``audio_path`` into ``video_path``, writing the
        result to ``out_path``. Returns True on success, False on any failure.

    is_enabled() -> bool
        Reads LUMEN_TTS_ENABLED. Cached per-process.

The full pipeline (worker.py): after stitching, if is_enabled(), synthesize a
WAV per scene from its caption, concat the WAVs, and mux into the stitched
video. Failure at any step falls back to the audio-less video.
"""
from __future__ import annotations

import os
import struct
import subprocess
import wave
from pathlib import Path


_TTS_ENABLED_ENV = "LUMEN_TTS_ENABLED"


def is_enabled() -> bool:
    """Read LUMEN_TTS_ENABLED (default off)."""
    return os.environ.get(_TTS_ENABLED_ENV, "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _write_silent_wav(out_path: str, duration_seconds: float = 1.0,
                      sample_rate: int = 22050) -> None:
    """Write a silent mono WAV the caller can still mux — fallback path.

    Uses the stdlib `wave` module so no extra deps. The silent track keeps
    the video duration aligned even if real TTS failed.
    """
    n_frames = int(sample_rate * max(0.05, duration_seconds))
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)            # 16-bit
        wf.setframerate(sample_rate)
        # All zero samples → silence
        wf.writeframes(struct.pack("<" + "h" * n_frames, *([0] * n_frames)))


def _try_edge_tts(text: str, out_path: str) -> bool:
    """Try Microsoft Edge's free TTS (online). Returns True on success."""
    try:
        import edge_tts  # type: ignore
    except ImportError:
        return False
    try:
        import asyncio
        voice = os.environ.get("LUMEN_TTS_VOICE", "en-US-AriaNeural")

        async def _run():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(out_path)

        asyncio.run(_run())
        return os.path.exists(out_path) and os.path.getsize(out_path) > 0
    except Exception as exc:
        print(f"[tts] edge-tts failed: {exc}")
        return False


def _try_pyttsx3(text: str, out_path: str) -> bool:
    """Try the offline SAPI/eSpeak TTS via pyttsx3. Returns True on success."""
    try:
        import pyttsx3  # type: ignore
    except ImportError:
        return False
    try:
        engine = pyttsx3.init()
        engine.save_to_file(text, out_path)
        engine.runAndWait()
        return os.path.exists(out_path) and os.path.getsize(out_path) > 0
    except Exception as exc:
        print(f"[tts] pyttsx3 failed: {exc}")
        return False


def synthesize(text: str, out_path: str) -> bool:
    """Synthesize ``text`` to ``out_path``. Never raises.

    Returns True if real audio was generated; False if a silent placeholder
    was written instead. The caller can mux either way.
    """
    text = (text or "").strip()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    if not text:
        # Nothing to say — write the minimum-duration silent WAV.
        _write_silent_wav(out_path, duration_seconds=0.5)
        return False

    if _try_edge_tts(text, out_path):
        return True
    if _try_pyttsx3(text, out_path):
        return True

    # Estimate duration from text length so the silent track roughly matches
    # what the audio WOULD have been (~150 wpm).
    word_count = max(1, len(text.split()))
    est_duration = (word_count / 150.0) * 60.0
    _write_silent_wav(out_path, duration_seconds=est_duration)
    return False


def mux_audio_into_video(video_path: str, audio_path: str,
                          out_path: str, timeout: int = 60) -> bool:
    """Mux ``audio_path`` into ``video_path`` via ffmpeg. Returns True on success.

    Uses ``-shortest`` so the muxed video doesn't extend past the shorter of
    the two tracks. ``-c:v copy`` avoids re-encoding the video for speed.
    """
    try:
        subprocess.run(
            ["ffmpeg", "-y",
             "-i", video_path,
             "-i", audio_path,
             "-c:v", "copy",
             "-c:a", "aac",
             "-shortest",
             out_path],
            check=True, capture_output=True, text=True, timeout=timeout,
        )
        return os.path.exists(out_path) and os.path.getsize(out_path) > 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        print(f"[tts] ffmpeg mux failed: {exc}")
        return False


def concat_audio_tracks(audio_paths: list[str], out_path: str,
                         timeout: int = 60) -> bool:
    """Concatenate WAV/MP3 tracks via ffmpeg concat demuxer."""
    if not audio_paths:
        return False
    list_path = out_path + ".txt"
    try:
        with open(list_path, "w") as fh:
            fh.write("\n".join(f"file '{p}'" for p in audio_paths))
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", list_path,
             "-c", "copy",
             out_path],
            check=True, capture_output=True, text=True, timeout=timeout,
        )
        return os.path.exists(out_path) and os.path.getsize(out_path) > 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        print(f"[tts] ffmpeg concat failed: {exc}")
        return False
    finally:
        try:
            os.remove(list_path)
        except OSError:
            pass
