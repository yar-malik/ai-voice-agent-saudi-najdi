# AI Voice Agent for Saudi Businesses — Najdi

> A phone agent that answers in Saudi Arabic, checks what is actually free, and books the appointment before the caller hangs up.

Built for Saudi Arabia. The agent speaks **Najdi Arabic** — the dialect of
Riyadh and central Saudi Arabia — and is written for the businesses that live
on their phone line: clinics, salons, workshops, anywhere a missed call is a
lost booking.

<p align="center">
  <a href="https://voho.ai/demos/appointment-booking">
    <img src="docs/demo.png" alt="A booking taken over the phone in Najdi Arabic: the caller asks for a dentist appointment, two free slots are offered, one is booked, and the Arabic confirmation SMS is sent" width="900">
  </a>
</p>

<p align="center">
  <b><a href="https://voho.ai/demos/appointment-booking">▶ Play the live demo</a></b> — runs in your browser, no sign-up.
</p>

<!-- voho:try -->
## Try it in your browser first

You do not have to clone anything to see whether this works for you. The same
engine this repository calls is running at **[app.voho.ai/agents](https://app.voho.ai/agents)** —
build an agent and talk to it out loud, in the browser, in about a minute.

New accounts start with **$25 of credit**, and one balance and one API key
cover every Voho product: AI Call Center, and the five beside it.

- **[Build an agent and talk to it out loud →](https://app.voho.ai/agents)**
- [Get an API key](https://app.voho.ai/tokens) — the key this repository needs
- [Read the API docs](https://docs.voho.ai)

Running it inside your own estate, against your own systems, is what we do
with you: [talk to us](https://voho.ai/book-demo).

---

---

## What this does

- Answers an inbound call in Najdi Arabic and works out what the caller wants.
- Reads **real availability** out of a calendar, offers slots on different days, and holds one while the caller decides.
- Books it, returns the reference number spoken digit by digit, and sends an Arabic confirmation SMS.
- Handles the awkward cases: the caller who does not say which slot, and the slot taken by someone else mid-call.

## Two ways to run this

**Let Voho be the whole agent.** A Voho voice agent answers the line, hears the
caller in Saudi Arabic, works out what they actually want, takes the action in
your systems, stops talking the moment it is interrupted, hands over to a
person when it should, and leaves a bilingual transcript and summary behind.
Hearing, deciding and speaking are all Voho's — you configure the agent and its
actions rather than writing any of this. It is the fastest route to a live
line.

**Or assemble it yourself, the way this repository does.** Here the
conversation lives in code you can read line by line, the tools are yours, and
Voho's Speech API provides the voice. Worth it when the script has to be
reviewed before it goes anywhere near a caller, or when every part has to sit
inside your own network.

| Part | In this repository | With a Voho agent |
| --- | --- | --- |
| Hearing the caller | whichever recogniser you point [`stt.py`](stt.py) at | Voho |
| Deciding what to do | the state machine in [`agent.py`](agent.py) | Voho |
| Acting in your systems | [`booking.py`](booking.py), against your calendar | Voho actions, calling your API |
| Speaking | Voho, via [`voho.py`](voho.py) | Voho |
| Transcript and summary | yours to keep | Voho, in Arabic and English |

Both end in the same place. Start with whichever suits the team you have.

## Quick start

One key, one command, about a minute. Get a key at
[app.voho.ai/tokens](https://app.voho.ai/tokens) — new accounts start with
**$25 of credit**, which is enough to run this many times over.

```bash
git clone https://github.com/yar-malik/ai-voice-agent-saudi-najdi.git
cd ai-voice-agent-saudi-najdi
export VOHO_API_KEY=voho_sk_live_...
```

### Node — no dependencies, Node 18+

```bash
npm start
# or: node examples/node/index.mjs ["what the caller says"]
```

### Python — no dependencies, Python 3.9+

```bash
python examples/python/main.py ["what the caller says"]
```

Either one speaks a line in Najdi Arabic and writes voho.mp3. Set VOHO_AGENT_ID and it holds a conversation instead, writing the reply as reply.mp3.

### Have it answer back

Speaking a line needs nothing but a key. To hold a conversation, create an
agent at [app.voho.ai/agents](https://app.voho.ai/agents) — pick a template,
edit the prompt — then take its id from the URL:

```bash
export VOHO_AGENT_ID=...        # from app.voho.ai/agents/<id>
npm start "أبي أعرف عن خدماتكم"
```

The agent answers from its own prompt, in its own voice, and `reply.mp3` is
what the caller would have heard.

## Voices

| Voice | Dialect | Use it for |
| --- | --- | --- |
| `layla` | **Najdi**, female | Reception and appointment setting. The default here. |
| `nouf` | **Najdi**, female | Measured and senior — reminders, escalations. |
| `faisal` | **Najdi**, male | Even and authoritative. Reads long text well. |
| `omar` | **Najdi**, male | Bright and quick. Confirmations and outbound. |
| `yousef` | Modern Standard, male | Safest when the caller's dialect is unknown. |

Set `VOHO_VOICE` in `.env`, or list them live:

```bash
curl "https://app.voho.ai/v1/voices?dialect=najdi" \
  -H "Authorization: Bearer $VOHO_API_KEY"
```

## Reading numbers out loud

`APT-20418` and `٤:٣٠` are exactly where a synthesiser guesses wrong. Two
things in this repository deal with it: reference numbers are spoken digit by
digit before they are sent to Voho, and [`voho.normalize()`](voho.py) will
expand numbers, dates and abbreviations the way they are actually said.

## Running inside your own network

Saudi enterprises frequently require that call audio does not leave the
building. Point `VOHO_BASE_URL` at your own deployment and set
`STT_PROVIDER=custom` with `STT_URL` pointing at a self-hosted recogniser —
nothing else in the code changes.

## Security

- No key is committed. `.env` is git-ignored; `.env.example` holds placeholders only.
- Synthesised clips are held in memory against a random id and dropped after they are played once.
- Rotate keys from the dashboard, and scope one key per environment.

## More Voho examples

| Repository | What it covers | Live demo |
| --- | --- | --- |
| [ai-voice-agent-saudi-najdi](https://github.com/yar-malik/ai-voice-agent-saudi-najdi) | Booking appointments by phone | [Play it](https://voho.ai/demos/appointment-booking) |
| [realtime-arabic-voice-agent-najdi](https://github.com/yar-malik/realtime-arabic-voice-agent-najdi) | Streaming answers from your own documents | [Play it](https://voho.ai/demos/realtime-arabic-rag) |
| [charco-voice-agent-najdi](https://github.com/yar-malik/charco-voice-agent-najdi) | Taking restaurant orders by phone | [Play it](https://voho.ai/demos/restaurant-ordering) |
| [saudi-arabic-voice-agent](https://github.com/yar-malik/saudi-arabic-voice-agent) | Phone agents in Najdi Arabic | [Play it](https://voho.ai/demos/ai-call-center) |
| [arabic-document-ai](https://github.com/yar-malik/arabic-document-ai) | Reading Saudi invoices, IDs and contracts | [Play it](https://voho.ai/demos/document-ai) |

## Want this in production?

We build the first workflow with you, on your own systems — usually live
within a month.

**[Book a call →](https://voho.ai/book-demo)**

---

MIT licensed. Built by [Voho](https://voho.ai) — enterprise AI for Saudi Arabia.
