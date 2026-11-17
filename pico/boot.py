import usb_audio
import usb_hid
import usb_midi
import supervisor

supervisor.set_usb_identification(manufacturer="Generic", product="USB Audio")

usb_midi.disable()  # frees USB endpoints for the audio device
usb_hid.enable((usb_hid.Device.KEYBOARD,))
# ponytail: 16 kHz mono is plenty to detect spikes; the PC resamples for us
usb_audio.enable(sample_rate=16000, channel_count=1, microphone=False, speaker=True)
