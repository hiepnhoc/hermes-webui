"""Regression coverage for hands-free voice mode using local server STT.

Arc can expose webkitSpeechRecognition and report a listening state while never
returning transcript events. Voice mode therefore needs a MediaRecorder path
that detects a pause, posts audio to /api/transcribe, and only uses browser
SpeechRecognition as a fallback.
"""
from pathlib import Path


BOOT = (Path(__file__).resolve().parents[1] / "static" / "boot.js").read_text(encoding="utf-8")


def _voice_mode_source() -> str:
    start = BOOT.index("// ── Turn-based voice mode")
    return BOOT[start:]


def test_voice_mode_accepts_media_recorder_as_stt_capability():
    src = _voice_mode_source()
    assert "navigator.mediaDevices" in src
    assert "navigator.mediaDevices.getUserMedia" in src
    assert "window.MediaRecorder" in src
    assert "SpeechRecognition||_voiceCanRecordAudio" in src


def test_voice_mode_records_until_silence_and_posts_to_local_transcriber():
    src = _voice_mode_source()
    assert "new MediaRecorder(" in src
    assert "createAnalyser()" in src
    assert "setInterval(monitor,100)" in src
    assert "_voiceSilenceMs()" in src
    assert "api/transcribe" in src
    assert "form.append('file'" in src
    assert "data.transcript" in src


def test_voice_mode_cleans_up_capture_on_deactivate():
    src = _voice_mode_source()
    deactivate = src[src.index("function _deactivate(){"):src.index("modeBtn.onclick")]
    assert "_stopVoiceCapture" in deactivate


def test_stale_recorder_callback_cannot_close_a_new_capture():
    src = _voice_mode_source()
    start = src.index("recorder.onstop=async()=>{")
    body = src[start:src.index("const blob=new Blob", start)]
    assert body.index("generation!==_voiceCaptureGeneration") < body.index("_cleanupVoiceCaptureResources()")


def test_server_stt_is_capability_gated_before_capture():
    src = _voice_mode_source()
    assert "fetch('api/transcribe/capability'" in src
    dispatcher = src[src.index("async function _startListening(){"):src.index("function _voiceModeSend(){")]
    assert "await _serverVoiceSttCapability" in dispatcher
    assert "_voiceCanRecordAudio&&serverSttAvailable" in dispatcher


def test_transcribe_failure_restores_listening_before_browser_fallback():
    src = _voice_mode_source()
    catch_start = src.index("}catch(_err){", src.index("const response=await fetch('api/transcribe'"))
    catch_body = src[catch_start:src.index("};", catch_start)]
    assert catch_body.index("_setState('listening')") < catch_body.index("_startBrowserListening()")


def test_media_recorder_constructor_is_guarded_and_mp4_is_labeled_m4a():
    src = _voice_mode_source()
    constructor = src[src.index("const preferredTypes="):src.index("_voiceRecorder=recorder")]
    assert "audio/mp4" in constructor
    assert "try{" in constructor and "new MediaRecorder(" in constructor
    assert "blobType.includes('mp4')?'m4a'" in src


def test_low_level_microphone_still_reaches_transcription_on_bounded_timer():
    src = _voice_mode_source()
    assert "!speechStarted&&now-captureStartedAt>=6000" in src
    assert "now-captureStartedAt>=15000" in src
    assert "discardCapture=true" not in src


def test_manual_send_invalidates_capture_and_transcript_is_session_pinned():
    src = _voice_mode_source()
    send_body = src[src.index("function _voiceModeSend(){"):src.index("function _speakResponse(){")]
    assert "_stopVoiceCapture(true)" in send_body
    assert "const captureSid=" in src
    assert "if(captureSid!==currentSid)" in src
