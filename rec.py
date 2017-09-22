#!/usr/bin/env python3
import argparse
import tempfile
import queue
import sys
import io
import wave
import time
import json
import uuid
import sys
from monotonic import monotonic
from urllib.parse import urlencode
from urllib.request import Request
from urllib.error import URLError
from urllib.error import HTTPError
from urllib.request import urlopen


FINAME = 'voice.wav'
BING_KEY = 'ba2c2f0fbe4440ec9191ce0f5e24cc96'
DEBUG_MODE = False
INTERVAL = 1 #seconds
    
def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


class RequestError(Exception):
    pass


class UnknownValueError(Exception):
    pass


class LocaleError(Exception):
    pass


class BingVoice():
    def __init__(self, key):
        self.key = key
        self.access_token = None
        self.expire_time = None
        self.locales = {
            "ar-eg": {"Female": "Microsoft Server Speech Text to Speech Voice (ar-EG, Hoda)"},
            "de-DE": {"Female": "Microsoft Server Speech Text to Speech Voice (de-DE, Hedda)",
                      "Male": "Microsoft Server Speech Text to Speech Voice (de-DE, Stefan, Apollo)"},
            "en-AU": {"Female": "Microsoft Server Speech Text to Speech Voice (en-AU, Catherine)"},
            "en-CA": {"Female": "Microsoft Server Speech Text to Speech Voice (en-CA, Linda)"},
            "en-GB": {"Female": "Microsoft Server Speech Text to Speech Voice (en-GB, Susan, Apollo)",
                      "Male": "Microsoft Server Speech Text to Speech Voice (en-GB, George, Apollo)"},
            "en-IN": {"Male": "Microsoft Server Speech Text to Speech Voice (en-IN, Ravi, Apollo)"},
            "en-US": {"Female": "Microsoft Server Speech Text to Speech Voice (en-US, ZiraRUS)",
                      "Male": "Microsoft Server Speech Text to Speech Voice (en-US, BenjaminRUS)"},
            "es-ES": {"Female": "Microsoft Server Speech Text to Speech Voice (es-ES, Laura, Apollo)",
                      "Male": "Microsoft Server Speech Text to Speech Voice (es-ES, Pablo, Apollo)"},
            "es-MX": {"Male": "Microsoft Server Speech Text to Speech Voice (es-MX, Raul, Apollo)"},
            "fr-CA": {"Female": "Microsoft Server Speech Text to Speech Voice (fr-CA, Caroline)"},
            "fr-FR": {"Female": "Microsoft Server Speech Text to Speech Voice (fr-FR, Julie, Apollo)",
                      "Male": "Microsoft Server Speech Text to Speech Voice (fr-FR, Paul, Apollo)"},
            "it-IT": {"Male": "Microsoft Server Speech Text to Speech Voice (it-IT, Cosimo, Apollo)"},
            "ja-JP": {"Female": "Microsoft Server Speech Text to Speech Voice (ja-JP, Ayumi, Apollo)",
                      "Male": "Microsoft Server Speech Text to Speech Voice (ja-JP, Ichiro, Apollo)"},
            "pt-BR": {"Male": "Microsoft Server Speech Text to Speech Voice (pt-BR, Daniel, Apollo)"},
            "ru-RU": {"Female": "Microsoft Server Speech Text to Speech Voice (pt-BR, Daniel, Apollo)",
                      "Male": "Microsoft Server Speech Text to Speech Voice (ru-RU, Pavel, Apollo)"},
            "zh-CN": {"Female": "Microsoft Server Speech Text to Speech Voice (zh-CN, HuihuiRUS)",
                      "Female2": "Microsoft Server Speech Text to Speech Voice (zh-CN, Yaoyao, Apollo)",
                      "Male": "Microsoft Server Speech Text to Speech Voice (zh-CN, Kangkang, Apollo)"},
            "zh-HK": {"Female": "Microsoft Server Speech Text to Speech Voice (zh-HK, Tracy, Apollo)",
                      "Male": "Microsoft Server Speech Text to Speech Voice (zh-HK, Danny, Apollo)"},
            "zh-TW": {"Female": "Microsoft Server Speech Text to Speech Voice (zh-TW, Yating, Apollo)",
                      "Male": "Microsoft Server Speech Text to Speech Voice (zh-TW, Zhiwei, Apollo)"}
        }

    def auth(self):
        if self.expire_time is None or monotonic() > self.expire_time:  # first credential request, or the access token from the previous one expired
            # get an access token using OAuth
            #credential_url = "https://oxford-speech.cloudapp.net/token/issueToken"
            credential_url = "https://api.cognitive.microsoft.com/sts/v1.0/issueToken"
            credential_request = Request(credential_url, data=urlencode({
                "grant_type": "client_credentials",
                "client_id": "python",
                "client_secret": self.key,
                "scope": "https://speech.platform.bing.com"
            }).encode("utf-8"), headers= {'content-type' : 'application/x-www-form-urlencoded', 'content-legth':0, 'Ocp-Apim-Subscription-Key' : self.key})
            start_time = monotonic()
            try:
                credential_response = urlopen(credential_request)
            except HTTPError as e:
                if DEBUG_MODE: print("fail token", e)
                raise RequestError("recognition request failed: {0}".format(
                    getattr(e, "reason", "status {0}".format(e.code))))  # use getattr to be compatible with Python 2.6
            except URLError as e:
                if DEBUG_MODE: print("fail token")
                raise RequestError("recognition connection failed: {0}".format(e.reason))
            credential_text = credential_response.read().decode("utf-8")
            if DEBUG_MODE: print("got token",credential_text)
            #credentials = json.loads(credential_text)
            self.access_token, expiry_seconds = credential_text, 1000000000

            self.expire_time = start_time + expiry_seconds

    def recognize(self, audio_data, language="en-US", show_all=False):
        self.auth()
        #wav_data = self.to_wav(audio_data)
        wav_data = audio_data
        url = "https://speech.platform.bing.com/recognize/query?{0}".format(urlencode({
            "version": "3.0",
            "requestid": uuid.uuid4(),
            "appID": "D4D52672-91D7-4C74-8AD8-42B1D98141A5",
            "format": "json",
            "locale": language,
            "device.os": "wp7",
            "scenarios": "ulm",
            "instanceid": uuid.uuid4(),
            "result.profanitymarkup": "0",
        }))
        request = Request(url, data=wav_data, headers={
            "Authorization": "Bearer {0}".format(self.access_token),
            "Content-Type": "audio/wav; samplerate=16000; sourcerate={0}; trustsourcerate=true".format(16000),
        })
        try:
            if DEBUG_MODE: print("opening the request")
            response = urlopen(request)
        except HTTPError as e:
            raise RequestError("recognition request failed: {0}".format(
                getattr(e, "reason", "status {0}".format(e.code))))  # use getattr to be compatible with Python 2.6
        except URLError as e:
            raise RequestError("recognition connection failed: {0}".format(e.reason))
        response_text = response.read().decode("utf-8")
        result = json.loads(response_text)

        # return results
        if show_all: return result
        if "header" not in result or "lexical" not in result["header"]: raise UnknownValueError()
        return result["header"]["lexical"]

    def synthesize(self, text, language="en-US", gender="Female"):
        self.auth()

        if language not in self.locales.keys():
            raise LocaleError("language locale not supported.")

        lang = self.locales.get(language)

        if gender not in ["Female", "Male", "Female2"]:
            gender = "Female"

        if len(lang) == 1:
            gender = lang.keys()[0]

        service_name = lang[gender]

        body = "<speak version='1.0' xml:lang='en-us'>\
                <voice xml:lang='%s' xml:gender='%s' name='%s'>%s</voice>\
                </speak>" % (language, gender, service_name, text)

        headers = {"Content-type": "application/ssml+xml",
                   "X-Microsoft-OutputFormat": "raw-16khz-16bit-mono-pcm",
                   "Authorization": "Bearer " + self.access_token,
                   "X-Search-AppId": "07D3234E49CE426DAA29772419F436CA",
                   "X-Search-ClientID": str(uuid.uuid1()).replace('-', ''),
                   "User-Agent": "TTSForPython"}

        url = "https://speech.platform.bing.com/synthesize"
        request = Request(url, data=body, headers=headers)
        try:
            response = urlopen(request)
        except HTTPError as e:
            raise RequestError("tts request failed: {0}".format(
                getattr(e, "reason", "status {0}".format(e.code))))  # use getattr to be compatible with Python 2.6
        except URLError as e:
            raise RequestError("tts connection failed: {0}".format(e.reason))

        data = response.read()

        return data

    @staticmethod
    def to_wav(raw_data):
        # generate the WAV file contents
        with io.BytesIO() as wav_file:
            wav_writer = wave.open(wav_file, "wb")
            try:  # note that we can't use context manager, since that was only added in Python 3.4
                wav_writer.setframerate(16000)
                wav_writer.setsampwidth(2)
                wav_writer.setnchannels(1)
                wav_writer.writeframes(raw_data)
                wav_data = wav_file.getvalue()
            finally:  # make sure resources are cleaned up
                wav_writer.close()
        return wav_data
    

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    '-l', '--list-devices', action='store_true',
    help='show list of audio devices and exit')
parser.add_argument(
    '-d', '--device', type=int_or_str,
    help='input device (numeric ID or substring)')
parser.add_argument(
    '-r', '--samplerate', type=int, help='sampling rate')
parser.add_argument(
    '-c', '--channels', type=int, default=1, help='number of input channels')
parser.add_argument(
    '-t', '--subtype', type=str, help='sound file subtype (e.g. "PCM_24")')
args = parser.parse_args()



try:
    import sounddevice as sd
    import soundfile as sf

    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    if args.samplerate is None:
        device_info = sd.query_devices(args.device, 'input')
        # soundfile expects an int, sounddevice provides a float:
        args.samplerate = 16000 
    q = queue.Queue()

    def callback(indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())
            
    # Make sure the file is opened before recording anything:
    with sd.InputStream(samplerate=args.samplerate, device=args.device,
                        channels=args.channels, callback=callback):
        print('#' * 20)
        print('press Ctrl+C to stop the recording')
        print('#' * 20)
        while True:
            if DEBUG_MODE: print('processing')         
            if DEBUG_MODE: print('create bing')    
            print("+")  
            bing = BingVoice(BING_KEY)
            with io.BytesIO() as wav_file:
                with sf.SoundFile(wav_file, mode='x', samplerate=args.samplerate,
                                  channels=args.channels, subtype=args.subtype, format='wav') as file:
                    while not q.empty():
                        temp = q.get()
                        file.write(temp)
                    # recognize speech using Microsoft Bing Voice Recognition
                    try:
                        if DEBUG_MODE: print('calling bing')   
                        text = bing.recognize(bytes(wav_file.getbuffer()), language='en-US')
                        print('Bing:', text.encode('utf-8'))
                    except UnknownValueError:
                        print("Microsoft Bing Voice Recognition could not understand audio")
                    except RequestError as e:
                        print("Could not request results from Microsoft Bing Voice Recognition service; {0}".format(e))
                    #raise KeyboardInterrupt("test")
            if DEBUG_MODE: print('sleeping to collect more sample')
            time.sleep(INTERVAL)   
    
except KeyboardInterrupt:
    print('\nRecording finished!')
    parser.exit(0)
except Exception as e:
    parser.exit(type(e).__name__ + ': ' + str(e))
