import requests
from requests.exceptions import ChunkedEncodingError
from monseigneur.core.tools.decorators import retry
from tempfile import NamedTemporaryFile
from .exceptions import Speech2TextException
import re
import speech_recognition as sr

class Speech2Text:

    def __init__(self):
        pass

    @retry(ChunkedEncodingError, tries=5, delay=1, backoff=1)
    def transcribe(self, audioUrl):
        # download the audio file from URL to a temporary file
        temp = NamedTemporaryFile()
        r = requests.get(audioUrl, allow_redirects=True)
        temp.write(r.content)
        temp.seek(0)

        r = sr.Recognizer()
        with sr.AudioFile(temp.name) as source:
            audio_data = r.record(source)
            try:
                text = r.recognize_sphinx(audio_data)
                print("speech to text : " + text)
            except Exception as e:
                raise Speech2TextException(e)

        result = text
        if not result:
            raise Speech2TextException('No result found')
        transcript = result.lower().replace('\n', ' ')

        replacements={'zero': 0, 'one': 1, 'to': 2, 'two': 2, 'three': 3, 'for': 4, 'four': 4, 'five': 5, 'six': 6, 'sex': 6, 'seven': 7, 'eight': 8, 'nine': 9}
        for k, v in replacements.items():
            transcript = transcript.replace(k, str(v))

        # remove all non-digit characters
        transcript = re.sub(r'\D', '', transcript)
        return transcript


if __name__ == '__main__':
    s2t = Speech2Text()
    code = s2t.transcribe('https://dd.prod.captcha-delivery.com/audio/2023-04-10/en/82ae0fd4e57ccf03bdc7b16903d871bc.wav')
    print(code)
