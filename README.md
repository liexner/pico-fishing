# pico-fishing

A Raspberry Pi Pico that auto-fishes in a single-player game. To the PC it shows up as
a USB speaker plus a USB keyboard. It listens to the game sound, recognises the bobber
splash of a bite, then presses space to reel in and space again to recast, with
human-like random delays.

## Setup

1. Install [CircuitPython](https://circuitpython.org/board/raspberry_pi_pico/) 10.x on the Pico.
2. Copy `pico/boot.py`, `pico/code.py` and `pico/bobber.py` to the `CIRCUITPY` drive, then unplug and replug the Pico.
3. Send the game's sound to the Pico as well as your headphones:
   - **Mac:** in Audio MIDI Setup, create a Multi-Output Device with your headphones plus "CircuitPython Speaker", and pick it as the sound output. Pick it again after each replug.
   - **Windows:** Sound settings → Recording → Stereo Mix → Listen to this device → the Pico. Or set the game's output to the Pico in Volume Mixer.
4. Cast once in the game and leave the game window focused. The Pico presses space by itself.

## How it works

- `bobber.py` holds spectral fingerprints (16 log-spaced bands, 0.5 s) of the game's three bobber sounds.
- `code.py` computes the same fingerprint over the incoming audio. A bite is when the match is 0.55 or higher.
- For the first 5 s after a cast it ignores matches, because the cast splash sounds like a bite.
- With no bite for 31 s it presses once and listens: a splash means it cast; otherwise it reeled in and casts again.

Tuning knobs are at the top of `code.py`. Watch the live log on the serial port, for example `screen /dev/cu.usbmodem101 115200`.

## Tools

- `tools/spacelog.swift` (macOS) logs your own space presses, to compare against the audio.
- `tools/match.py` and `tools/sim2.py` replay raw recordings (made with `RECORD = True`) through the detector.
