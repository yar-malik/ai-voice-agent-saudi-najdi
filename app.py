"""Flask + Twilio: the phone end.

Twilio calls this app once per turn. Each turn we take what the caller said,
ask the agent what to say back, synthesise it with Voho, and hand Twilio a URL
to play. The audio is kept in memory against a short-lived id rather than
written to disk — a booking call is five turns and none of it needs to
outlive the call.

Point a Twilio number's Voice webhook at POST /voice and it works.
"""

from __future__ import annotations

import os
import secrets
import threading
from typing import Dict, Tuple

from dotenv import load_dotenv
from flask import Flask, Response, request, url_for

load_dotenv()

import agent as agent_mod  # noqa: E402  (after load_dotenv, so env is populated)
import booking  # noqa: E402
import voho  # noqa: E402

app = Flask(__name__)
booking.init_db()

# call sid -> Agent, and clip id -> audio. Both die with the process, which is
# correct for an example and wrong for production: use Redis if you run more
# than one worker, or Twilio will hit a worker that has never heard the call.
_calls: Dict[str, agent_mod.Agent] = {}
_clips: Dict[str, Tuple[bytes, str]] = {}
_lock = threading.Lock()

PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")


def _clip(text: str) -> str:
    """Synthesise a line and return the URL Twilio should play."""
    audio = voho.speak(text, fmt="mp3")
    clip_id = secrets.token_urlsafe(12)
    with _lock:
        _clips[clip_id] = (audio, "audio/mpeg")
    path = url_for("clip", clip_id=clip_id)
    return f"{PUBLIC_URL}{path}" if PUBLIC_URL else path


def _twiml(say_url: str, *, listen: bool) -> Response:
    """Play a line, then either listen for the next turn or hang up."""
    if listen:
        body = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" language="ar-SA" speechTimeout="auto" action="/voice/turn" method="POST">
    <Play>{say_url}</Play>
  </Gather>
  <Redirect method="POST">/voice/turn</Redirect>
</Response>"""
    else:
        body = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Play>{say_url}</Play>
  <Hangup/>
</Response>"""
    return Response(body, mimetype="text/xml")


@app.post("/voice")
def voice():
    """A call has come in."""
    call_sid = request.form.get("CallSid", secrets.token_urlsafe(8))
    caller = request.form.get("From", "unknown")
    convo = agent_mod.Agent(caller=caller)
    with _lock:
        _calls[call_sid] = convo
    return _twiml(_clip(convo.greeting()), listen=True)


@app.post("/voice/turn")
def turn():
    """The caller said something."""
    call_sid = request.form.get("CallSid", "")
    said = request.form.get("SpeechResult", "").strip()

    with _lock:
        convo = _calls.get(call_sid)
    if convo is None:
        # Worker restarted, or Twilio is talking to a different one.
        return _twiml(_clip("معليش، صار عندنا خلل تقني. جرب تتصل مرة ثانية."), listen=False)

    if not said:
        return _twiml(_clip("ما سمعتك زين. تقدر تعيد؟"), listen=True)

    answer = convo.reply(said)
    done = convo.state.finished

    if done:
        sms = convo.confirmation_sms()
        if sms:
            _send_sms(convo.state.caller, sms)

    return _twiml(_clip(answer), listen=not done)


@app.get("/clip/<clip_id>")
def clip(clip_id: str):
    """Twilio fetches the audio it was told to play."""
    with _lock:
        found = _clips.pop(clip_id, None)  # played once, then gone
    if not found:
        return Response(status=404)
    audio, content_type = found
    return Response(audio, mimetype=content_type)


@app.get("/health")
def health():
    return {"ok": True, "voice": voho.DEFAULT_VOICE, "model": voho.DEFAULT_MODEL}


def _send_sms(to: str, body: str) -> None:
    """Confirmation by text. Skipped quietly if Twilio is not configured."""
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    if not (sid and token and from_number):
        app.logger.info("SMS not sent (Twilio not configured): %s", body)
        return
    try:
        from twilio.rest import Client

        Client(sid, token).messages.create(to=to, from_=from_number, body=body)
    except Exception as exc:  # noqa: BLE001 — a failed SMS must not fail the call
        app.logger.warning("SMS failed: %s", exc)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
