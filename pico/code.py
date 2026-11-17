import array
import math
import random
import time
import usb_audio
import usb_hid
import ulab.numpy as np
from bobber import BANDS, FRAMES, TEMPLATES

# --- tuning knobs ---
RECORD = False       # True = stream raw audio to the Mac over serial, nothing else
ARMED = True         # False = only log, never press space
REACT = True         # False = ignore bites, only recast every CAST_TIMEOUT (for recording)
MATCH = 0.55         # bite = fingerprint match >= MATCH (bites scored 0.60-0.94 at both spots)
SPLASH = 10.0        # timeout probe: high-pitch energy > SPLASH x ambient = the press cast the line
                     # (casts 14-129, reel-in presses 3-6 across spots)
AMBIENT_SECS = 1.0   # how many seconds of sound the ambient average covers
MIN_AMBIENT = 2000.0 # floor for the ambient average (0 = game silent)
REEL_DELAY = (0.1, 0.6)    # random wait (s) after a match; the match itself already takes ~0.5 s
RECAST_DELAY = (0.5, 2.0)  # random wait (s) between reel-in and recast
DISTRACTED = (0.15, 1.0, 4.0)  # 15% of recasts wait an extra 1-4 s, like a human looking away
IGNORE_AFTER_CAST = 5.0    # cast splash can ring for ~4s and looks like a bite
CAST_TIMEOUT = 31.0        # no bite heard in 31 s: press, and recast if that press reeled in
PRINT_EVERY = 0.1    # seconds between log lines

HOP = 256            # 16 ms of audio per analysis step; frames are 2 hops (32 ms)
SPACE = bytes([0, 0, 0x2C, 0, 0, 0, 0, 0])
RELEASE = bytes(8)

kbd = usb_hid.devices[0]
spk = usb_audio.usb_speaker
buf = array.array("h", [0] * HOP)
HANN = np.array([0.5 - 0.5 * math.cos(2 * math.pi * i / (2 * HOP - 1)) for i in range(2 * HOP)])
TPL = [np.array(t).reshape((FRAMES, len(BANDS))) for t in TEMPLATES]


def tap():
    kbd.send_report(SPACE)
    time.sleep(random.uniform(0.04, 0.09))
    kbd.send_report(RELEASE)


def drain():
    global pos, filled
    while spk.read(buf, len(buf)):
        pass
    pos = 0
    filled = 0  # audio was skipped, history is no longer continuous


def recast_wait():
    w = random.uniform(*RECAST_DELAY)
    if random.random() < DISTRACTED[0]:
        w += random.uniform(DISTRACTED[1], DISTRACTED[2])
    time.sleep(w)


def cast():
    global cast_at
    tap()
    print("CAST")
    cast_at = time.monotonic()


def step():
    """Read audio; once a full hop is in, return (level, score). None while waiting for audio.
    level = high-pitch energy x ambient (cast splash check); score = best fingerprint match."""
    global pos, win, hist, ambient, filled
    n = spk.read(buf, HOP - pos)
    if not n:
        return None
    pending[pos:pos + n] = np.array(np.frombuffer(buf, dtype=np.int16)[:n], dtype=np.float)
    pos += n
    if pos < HOP:
        return None
    pos = 0
    win = np.concatenate((win[HOP:], pending))

    # loudness of the high pitches (2nd difference), vs a slowly updated ambient average
    d = np.diff(win[HOP - 2:], n=2)
    energy = float(np.sum(d * d))
    level = energy / max(ambient, MIN_AMBIENT)
    ambient += (min(energy, 3 * ambient) - ambient) * (HOP / 16000 / AMBIENT_SECS)

    # fingerprint: log energy in 16 bands, compared to the game's bobber sound over the last 0.5 s
    re, im = np.fft.fft((win - np.mean(win)) * HANN)
    p = re * re + im * im
    # only compare once we hold 0.5 s of real sound: "silence, then sound" looks like a splash onset
    filled = 0 if float(np.sum(p)) < 1.0 else filled + 1
    row = np.array([math.log(float(np.sum(p[a:b])) + 1e-3) for a, b in BANDS])
    hist = np.roll(hist, -1, axis=0)
    hist[FRAMES - 1, :] = row
    w = hist - np.mean(hist)
    norm = math.sqrt(float(np.sum(w * w))) or 1.0
    if filled < FRAMES:
        return level, 0.0
    score = max(float(np.sum(w * t)) for t in TPL) / norm
    return level, score


if RECORD:
    import usb_cdc
    while True:
        n = spk.read(buf, len(buf))
        if n:
            usb_cdc.console.write(memoryview(buf)[:n])

pending = np.zeros(HOP)
win = np.zeros(2 * HOP)
hist = np.zeros((FRAMES, len(BANDS)))
pos = 0
filled = 0
ambient = MIN_AMBIENT
cast_at = time.monotonic() - CAST_TIMEOUT - 1  # probe at startup: press once, listen for a splash
best = 0.0
last_print = time.monotonic()

while True:
    now = time.monotonic()

    if ARMED and now - cast_at > CAST_TIMEOUT:
        # we don't know if the line is out: press once and listen for a cast splash
        print("TIMEOUT")
        tap()
        t = time.monotonic()
        drain()
        heard = -1.0  # stays -1 if no audio arrived at all
        while time.monotonic() - t < 1.5:
            r = step()
            if r:
                heard = max(heard, r[0])
        if heard < 0.5:  # nothing, or pure digital silence (game audio not reaching us)
            print("NO AUDIO: not pressing again, next check in", CAST_TIMEOUT, "s")
            cast_at = t  # ponytail: worst case we idle one timeout
        elif heard > SPLASH:
            print("CAST (timeout press cast the line)", int(heard))
            cast_at = t
        else:
            print("REEL (timeout press reeled in)", int(heard))
            recast_wait()
            cast()
            drain()
        continue

    r = step()
    if r is None:
        time.sleep(0.001)
        continue
    level, score = r
    best = max(best, score)

    # ponytail: no splash re-check after our own casts; it misjudged quiet casts and aborted
    # them. A failed cast is caught by the timeout probe below within CAST_TIMEOUT.
    listening = now - cast_at > IGNORE_AFTER_CAST

    if ARMED and REACT and listening and score >= MATCH:
        print("BITE match", round(score, 2))
        time.sleep(random.uniform(*REEL_DELAY))
        tap()
        print("REEL")
        recast_wait()
        cast()
        drain()  # throw away audio that piled up while we waited
        continue

    if now - last_print > PRINT_EVERY:
        print("match", round(best, 2), "lvl", round(level, 1))  # bite fires at MATCH
        best = 0.0
        last_print = now
