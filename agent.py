"""The conversation.

One class, one method: `reply(caller, said)` takes what the caller just said
and returns what to say back, having done whatever the answer implied — a
calendar lookup, a hold, a booking.

The state machine is deliberately explicit rather than left to a model. For
booking, the set of things a caller can want is small and the cost of an
imagined appointment is high, so the model (if you enable one) is used for
understanding the request, never for deciding that a slot exists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

import booking

# Services the clinic offers, and the words callers actually use for them.
SERVICES = {
    "dentistry": ["أسنان", "سن", "ضرس", "تقويم", "dentist", "teeth", "tooth"],
    "general": ["عام", "كشف", "فحص", "دكتور", "طبيب", "general", "check"],
}

YES = ["إيه", "ايه", "نعم", "أجل", "تمام", "زين", "اوكي", "أوكي", "yes", "ok", "sure"]
FIRST = ["الأول", "الاول", "الأولى", "first", "one"]
SECOND = ["الثاني", "الثانية", "الأخير", "second", "two"]


@dataclass
class CallState:
    caller: str
    service: str | None = None
    offered: list[booking.Slot] = field(default_factory=list)
    reference: str | None = None
    finished: bool = False


def _match_service(said: str) -> str | None:
    lowered = said.lower()
    for service, words in SERVICES.items():
        if any(w in lowered for w in words):
            return service
    return None


def _chose(said: str, offered: list[booking.Slot]) -> booking.Slot | None:
    """Work out which of the offered slots the caller picked.

    Callers rarely say "the first one". They say the day, or the time, or
    something that only makes sense against what was just offered.
    """
    lowered = said.lower()
    for slot in offered:
        day_ar = slot.spoken_ar().split(" ")[0]
        if day_ar in said:
            return slot
        if str(slot.starts_at.hour) in said or f"{slot.starts_at.hour}:{slot.starts_at.minute:02d}" in said:
            return slot
    if any(w in lowered for w in FIRST) and offered:
        return offered[0]
    if any(w in lowered for w in SECOND) and len(offered) > 1:
        return offered[1]
    if any(w in lowered for w in YES) and offered:
        return offered[0]
    return None


class Agent:
    """One instance per call."""

    GREETING = "عيادة النخبة، معك ليلى. كيف أقدر أساعدك؟"

    def __init__(self, caller: str) -> None:
        self.state = CallState(caller=caller)

    def greeting(self) -> str:
        return self.GREETING

    def reply(self, said: str) -> str:
        st = self.state

        if st.finished:
            return "تم حجز موعدك. تحتاج شي ثاني؟"

        # 1. what does the caller want
        if st.service is None:
            st.service = _match_service(said)
            if st.service is None:
                return "أكيد. الموعد لعيادة الأسنان ولا كشف عام؟"

        # 2. offer what is actually free
        if not st.offered:
            st.offered = booking.availability(st.service)
            if not st.offered:
                return (
                    "ما عندنا مواعيد فاضية هالأسبوع. أقدر أسجل رقمك ونتواصل معك "
                    "أول ما ينفتح موعد؟"
                )
            for slot in st.offered:
                booking.hold(slot.id)
            spoken = "، أو ".join(s.spoken_ar() for s in st.offered)
            return f"عندنا {spoken}. أيهم يناسبك؟"

        # 3. book the one they picked
        chosen = _chose(said, st.offered)
        if chosen is None:
            spoken = "، أو ".join(s.spoken_ar() for s in st.offered)
            return f"عشان أتأكد — {spoken}. أي وحدة أحجز لك؟"

        reference = booking.book(chosen.id, st.caller)
        if reference is None:
            # Someone else took it between the offer and the answer.
            st.offered = []
            return "معليش، هالموعد انحجز قبل شوي. لحظة أشوف لك بديل."

        st.reference = reference
        st.finished = True
        digits = " ".join(reference.split("-")[1])
        return (
            f"تم الحجز {chosen.spoken_ar()} مع {chosen.practitioner}. "
            f"رقم الموعد {digits}. راح يوصلك تأكيد برسالة نصية الحين."
        )

    def confirmation_sms(self) -> str | None:
        """The text message, in Arabic, sent once the booking exists."""
        if not self.state.reference:
            return None
        appt = booking.lookup(self.state.reference)
        if not appt:
            return None
        slot = booking.Slot(
            id=0,
            starts_at=datetime.fromisoformat(appt["starts_at"]),
            practitioner=appt["practitioner"],
            service=appt["service"],
        )
        return (
            f"تم تأكيد موعدك في عيادة النخبة، {slot.spoken_ar()} "
            f"مع {appt['practitioner']}. رقم الموعد {appt['reference']}."
        )


def strip_tashkeel(text: str) -> str:
    """Remove Arabic diacritics before matching, never before speaking.

    Voho reads tashkeel correctly; string comparison does not.
    """
    return re.sub(r"[ً-ْ]", "", text)
