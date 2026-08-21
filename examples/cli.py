"""The whole booking flow, in a terminal. No phone number needed.

    python examples/cli.py

Type in Arabic the way a caller would speak. Each reply is synthesised with
Voho and written to out/, so you can hear what the caller would have heard.
Pass --silent to skip synthesis and just read the conversation.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import agent as agent_mod  # noqa: E402
import booking  # noqa: E402
import voho  # noqa: E402

OUT = Path("out")
SILENT = "--silent" in sys.argv

# A caller who books a dentist appointment, if you would rather not type.
SCRIPT = [
    "أبغى موعد عند دكتور أسنان الأسبوع الجاي",
    "تمام، خلها الموعد الأول",
]


def say(turn: int, text: str) -> None:
    print(f"\n  \033[32mVoho\033[0m  {text}")
    if SILENT:
        return
    try:
        audio = voho.speak(text)
    except voho.VohoError as exc:
        print(f"        (not synthesised: {exc})")
        return
    OUT.mkdir(exist_ok=True)
    path = OUT / f"turn-{turn:02d}.mp3"
    path.write_bytes(audio)
    print(f"        \033[2m{path} · {len(audio) // 1024} KB · voice {voho.DEFAULT_VOICE}\033[0m")


def main() -> None:
    booking.init_db()
    convo = agent_mod.Agent(caller=os.getenv("TEST_CALLER", "+966500000000"))

    print("\033[2m  Type what the caller says. Enter on its own runs the script. Ctrl-C to stop.\033[0m")
    turn = 0
    say(turn, convo.greeting())

    scripted = iter(SCRIPT)
    while not convo.state.finished:
        try:
            said = input("\n  Caller  ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not said:
            said = next(scripted, "")
            if not said:
                print("  (script finished)")
                return
            print(f"  Caller  {said}")

        turn += 1
        say(turn, convo.reply(said))

    sms = convo.confirmation_sms()
    if sms:
        print(f"\n  \033[2mSMS →\033[0m {sms}")
    print(f"\n  \033[2mReference {convo.state.reference} is now in {booking.DB_PATH}\033[0m\n")


if __name__ == "__main__":
    main()
