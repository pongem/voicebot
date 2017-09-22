import pyaudio, wave, time, sys
from datetime import datetime

CHUNK = 8192
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5

current_time = str(datetime.now())  #"Date/Time for File Name"
current_time = "_".join(current_time.split()).replace(":","-")
current_time = current_time[:-7]
WAVE_OUTPUT_FILENAME = 'Audio_'+current_time+'.wav'

p = pyaudio.PyAudio()

stream = p.open(format=FORMAT, channels = CHANNELS, rate = RATE, input = True, input_device_index = 0, frames_per_buffer = CHUNK)

print("* recording")

frames = []
for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    print(i)
    data = stream.read(CHUNK)
    frames.append(data)

print("* done recording")

stream.stop_stream()
stream.close()
p.terminate()

wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()
