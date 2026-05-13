"""Tests for the optional TTS narration pipeline (Item #8)."""
import os
import sys
import wave

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent import tts


def test_is_enabled_default_off(monkeypatch):
    monkeypatch.delenv("LUMEN_TTS_ENABLED", raising=False)
    assert tts.is_enabled() is False


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "yes", "on"])
def test_is_enabled_truthy_values(monkeypatch, val):
    monkeypatch.setenv("LUMEN_TTS_ENABLED", val)
    assert tts.is_enabled() is True


def test_synthesize_writes_silent_wav_when_no_providers(tmp_path, mocker):
    """With no providers available, synthesize writes a silent WAV and returns False."""
    mocker.patch("agent.tts._try_edge_tts", return_value=False)
    mocker.patch("agent.tts._try_pyttsx3", return_value=False)
    out = tmp_path / "out.wav"
    result = tts.synthesize("hello world", str(out))
    assert result is False
    assert out.exists()
    with wave.open(str(out), "rb") as wf:
        # Silent track was written — must be a readable WAV
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2


def test_synthesize_empty_text_writes_short_silent_track(tmp_path, mocker):
    mocker.patch("agent.tts._try_edge_tts", return_value=False)
    mocker.patch("agent.tts._try_pyttsx3", return_value=False)
    out = tmp_path / "out.wav"
    result = tts.synthesize("", str(out))
    assert result is False
    assert out.exists()


def test_synthesize_prefers_edge_then_pyttsx3(tmp_path, mocker):
    """Provider chain: edge-tts first, pyttsx3 second."""
    edge = mocker.patch("agent.tts._try_edge_tts", return_value=True)
    pytt = mocker.patch("agent.tts._try_pyttsx3", return_value=True)
    out = tmp_path / "x.wav"
    # Edge succeeds — pyttsx3 must NOT be called
    result = tts.synthesize("hi", str(out))
    assert result is True
    edge.assert_called_once()
    pytt.assert_not_called()

    edge.reset_mock()
    pytt.reset_mock()
    mocker.patch("agent.tts._try_edge_tts", return_value=False)
    pytt2 = mocker.patch("agent.tts._try_pyttsx3", return_value=True)
    out2 = tmp_path / "y.wav"
    result = tts.synthesize("hi", str(out2))
    assert result is True
    pytt2.assert_called_once()


def test_mux_audio_into_video_invokes_ffmpeg(mocker, tmp_path):
    """The mux helper must shell out to ffmpeg with -c:v copy + -shortest."""
    # Pretend ffmpeg succeeds and the output file exists
    run = mocker.patch("agent.tts.subprocess.run")
    # File-existence check uses os.path.exists / getsize against out_path
    out_path = str(tmp_path / "out.mp4")
    with open(out_path, "wb") as fh:
        fh.write(b"x" * 100)  # non-empty so getsize > 0
    ok = tts.mux_audio_into_video("v.mp4", "a.wav", out_path)
    assert ok is True
    cmd = run.call_args[0][0]
    assert "ffmpeg" in cmd[0]
    assert "-c:v" in cmd and "copy" in cmd
    assert "-shortest" in cmd


def test_mux_audio_returns_false_on_ffmpeg_error(mocker):
    import subprocess
    mocker.patch("agent.tts.subprocess.run",
                  side_effect=subprocess.CalledProcessError(1, "ffmpeg"))
    ok = tts.mux_audio_into_video("v.mp4", "a.wav", "out.mp4")
    assert ok is False


def test_worker_skips_tts_when_disabled(monkeypatch, mocker, tmp_path):
    """The worker's TTS hook must no-op when LUMEN_TTS_ENABLED is unset."""
    from renderer import worker
    monkeypatch.delenv("LUMEN_TTS_ENABLED", raising=False)
    synth = mocker.patch("agent.tts.synthesize")
    worker._maybe_apply_tts("jid", [
        type("S", (), {"caption": "hello"})(),
    ], str(tmp_path / "stub.mp4"))
    synth.assert_not_called()


def test_worker_runs_tts_when_enabled(monkeypatch, mocker, tmp_path):
    """When enabled, the worker calls synthesize per step and tries to mux."""
    from renderer import worker
    monkeypatch.setenv("LUMEN_TTS_ENABLED", "1")
    # Stub out the actual providers + ffmpeg
    mocker.patch("agent.tts._try_edge_tts", return_value=False)
    mocker.patch("agent.tts._try_pyttsx3", return_value=False)

    concat = mocker.patch("agent.tts.concat_audio_tracks", return_value=True)
    mux = mocker.patch("agent.tts.mux_audio_into_video", return_value=True)

    # Make replace a no-op so we don't need a real muxed file
    mocker.patch("renderer.worker.os.replace")

    stub_path = str(tmp_path / "stitched.mp4")
    with open(stub_path, "wb") as fh:
        fh.write(b"v" * 50)

    steps = [
        type("S", (), {"caption": "first"})(),
        type("S", (), {"caption": "second"})(),
    ]
    worker._maybe_apply_tts("test-jid", steps, stub_path)
    # Both helpers should have been called
    concat.assert_called_once()
    mux.assert_called_once()
