from flask import Flask, request, jsonify
from pocketsphinx import pocketsphinx
from pydub import AudioSegment
import os
import glob

app = Flask(__name__)


def convert_to_wav(input_file, output_file):
    audio = AudioSegment.from_file(input_file)
    audio = audio.set_frame_rate(16000)
    audio = audio.set_sample_width(2)
    audio = audio.set_channels(1)
    audio.export(output_file, format='wav')


def transcribe_audio(audio_file, acoustic_model, language_model, phonetic_dictionary):
    config = pocketsphinx.Config()
    config.set_string('-hmm', acoustic_model)
    config.set_string('-lm', language_model)
    config.set_string('-dict', phonetic_dictionary)
    config.set_string('-topn', '1')

    decoder = pocketsphinx.Decoder(config)

    with open(audio_file, 'rb') as audio_file:
        decoder.start_utt()
        while True:
            buf = audio_file.read(1024)
            if buf:
                decoder.process_raw(buf, False, False)
            else:
                break
        decoder.end_utt()

    transcript = decoder.hyp().hypstr if decoder.hyp() else None
    return transcript


def extract_keywords(transcript):
    stopwords = ['እና', 'እስከ', 'ወደ', 'ስለ', 'ግን', 'እንዲሁም', 'ለ', 'በ', 'የ', 'ከ']
    words = transcript.lower().split()
    cleaned_words = [word.strip('.,?!') for word in words if word not in stopwords]
    word_counts = {}
    for word in cleaned_words:
        if word in word_counts:
            word_counts[word] += 1
        else:
            word_counts[word] = 1
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    top_keywords = [word for word, count in sorted_words[:10]]
    if len(top_keywords) >= 10:
        top_keywords = top_keywords[:5]
    return top_keywords


def search_transcripts(audio_files, keywords, acoustic_model_path, language_model_path, phonetic_dictionary_path):
    matches = []
    for audio_file in audio_files:
        transcript = transcribe_audio(audio_file, acoustic_model_path, language_model_path, phonetic_dictionary_path)
        for keyword in keywords:
            if transcript and keyword.lower() in transcript.lower():
                matches.append((audio_file, transcript))
                break
    return matches


@app.route('/api/convert', methods=['POST'])
def convert_audio():
    # API endpoint for converting audio to WAV
    # Accepts JSON payload with "input_file" field
    data = request.get_json()
    input_file = data.get('input_file')

    # Generate the output file path by adding the ".wav" extension to the input file
    output_file = os.path.splitext(input_file)[0] + '.wav'

    convert_to_wav(input_file, output_file)
    return jsonify(message='Audio converted successfully.', output_file=output_file)


@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    # API endpoint for audio transcription
    # Accepts JSON payload with audio_file, acoustic_model, language_model, and phonetic_dictionary fields
    data = request.get_json()
    audio_file = data.get('audio_file')
    language_model = data.get('language_model')
    phonetic_dictionary = data.get('phonetic_dictionary')
    acoustic_model = data.get('acoustic_model')
    transcript = transcribe_audio(audio_file, acoustic_model, language_model, phonetic_dictionary)
    return jsonify(transcript=transcript)


@app.route('/api/search', methods=['POST'])
def search():
    # API endpoint for searching transcripts
    # Accepts JSON payload with audio_files, input_audio, acoustic_model, language_model, and phonetic_dictionary fields
    data = request.get_json()
    audio_files = data.get('audio_files')
    input_audio = data.get('input_audio')
    acoustic_model = data.get('acoustic_model')
    language_model = data.get('language_model')
    phonetic_dictionary = data.get('phonetic_dictionary')

    # Convert input audio to WAV
    converted_audio = os.path.splitext(input_audio)[0] + '.wav'
    convert_to_wav(input_audio, converted_audio)

    # Transcribe input audio
    transcript = transcribe_audio(converted_audio, acoustic_model, language_model, phonetic_dictionary)

    # Extract keywords from transcript
    keywords = extract_keywords(transcript)

    # Search transcripts in the audio files using the keywords
    matching_results = search_transcripts(
        audio_files,
        keywords,
        acoustic_model,      # Provide the correct acoustic model path here
        language_model,      # Provide the correct language model path here
        phonetic_dictionary  # Provide the correct phonetic dictionary path here
    )


    return jsonify(matches=matching_results)


if __name__ == '__main__':
    app.run()
