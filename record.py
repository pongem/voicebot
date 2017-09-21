
import sounddevice as sd

duration = 5.5
fs = 48000
print("start recording")
mr = sd.rec( int(duration * fs), samplerate = fs, channels=1)
sd.wait()
print("end recording and start playing")
sd.play(mr, fs)
sd.wait()
