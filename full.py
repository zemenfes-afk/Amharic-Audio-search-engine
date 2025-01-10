    from flask import Flask, request, jsonify
    from pydub import AudioSegment
    from werkzeug.utils import secure_filename
    import os
    import glob
    from flask_cors import CORS
    import requests

    app = Flask(__name__)
    CORS(app)

    # Global variable for keywords
    global_keywords = []


    # Function to convert audio to WAV
    def convert_to_wav(input_file, output_file):
        input_extension = os.path.splitext(input_file)[1].lower()

        if input_extension == '.wav':
            # For .wav files, modify specific properties and save
            audio = AudioSegment.from_file(input_file)
            audio = audio.set_frame_rate(16000)
            audio = audio.set_sample_width(2)
            audio = audio.set_channels(1)
            audio.export(output_file, format='wav')
        else:
            # For non-.wav files, convert to .wav with specific properties and save
            audio = AudioSegment.from_file(input_file)
            audio = audio.set_frame_rate(16000)
            audio = audio.set_sample_width(2)
            audio = audio.set_channels(1)
            audio.export(output_file, format='wav')


    # Define the endpoint URL of the external transcription API
    EXTERNAL_TRANSCRIPTION_API_URL = "http://192.168.43.79:8080/transcribe"


    # Function to transcribe using an external API
    def transcribe_external(audio_path):
        with open(audio_path, 'rb') as audio_file:
            files = {'audio': audio_file}
            response = requests.post(EXTERNAL_TRANSCRIPTION_API_URL, files=files)
            input_audio_path = r'C:\CMU\Amharic1\search\MWCone4.wav'
            list_of_audio_folder = r'C:\CMU\Amharic1\list'
            return response.json()


    # Function to extract keywords from a transcript
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
        keywords = [word for word, count in sorted_words[:10]]
        if len(keywords) >= 10:
            keywords = keywords[:5]
        return keywords


    # Function to search transcripts for keywords
    def search_transcripts(transcripts, keywords):
        matching_results = []
        for audio_file, transcript in transcripts.items():
            for keyword in keywords:
                if transcript and keyword.lower() in transcript.lower():
                    matching_results.append((audio_file, transcript))
                    break
        return matching_results


    # Route to transcribe a list of audio files
    @app.route('/transcribe_list', methods=['POST'])
    def transcribe_list_route():
        try:
            # Define the paths to the input audio file and the list of audio files
            input_audio_path = r'C:\CMU\Amharic1\search\MWCone4.wav'
            list_of_audio_folder = r'C:\CMU\Amharic1\list'

            # Get the input audio file and list of audio files from the request
            input_audio = request.files['input_audio']
            input_audio_path = os.path.join(os.path.dirname(__file__), secure_filename(input_audio.filename))
            input_audio.save(input_audio_path)

            list_of_audios = request.files.getlist('list_of_audios')
            list_of_audios_paths = []

            for audio in list_of_audios:
                audio_path = os.path.join(os.path.dirname(__file__), secure_filename(audio.filename))
                audio.save(audio_path)
                list_of_audios_paths.append(audio_path)

            # Transcribe the input audio file
            transcripts = {}
            response_input = transcribe_external(input_audio_path)
            transcripts['input_audio'] = response_input['text']

            # Transcribe the list of audio files
            list_transcripts = {}

            for audio_path in list_of_audios_paths:
                response = transcribe_external(audio_path)
                list_transcripts[audio_path] = response['text']

            transcripts['list_of_audios'] = list_transcripts

            response = {
                'transcript_input': response_input['text'],  # Include the input transcript
                'transcript_list': list_transcripts
            }

            return jsonify(response)

        except FileNotFoundError as e:
            return jsonify({'error': 'File not found'}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500


    # Route to extract keywords from a transcript
    @app.route('/extract_keywords', methods=['POST'])
    def extract_keywords_route():
        try:
            # Get the transcript input from form data
            response_input = request.form.get('transcript_input')

            if not response_input:
                return jsonify({'error': 'No transcript input provided'})

            keywords = extract_keywords(response_input)  # Extract keywords
            global global_keywords
            global_keywords = keywords  # Store the extracted keywords

            return jsonify({'keywords': keywords})

        except Exception as e:
            return jsonify({'error': str(e)})


    # Route to search transcripts for keywords
    @app.route('/search', methods=['POST'])
    def search_route():
        try:
            request_data = request.get_json()
            list_transcripts = request_data.get('list_transcripts')  # Get list of transcripts from JSON

            if not list_transcripts:
                return jsonify({'error': 'No list of transcripts provided'})

            keywords = global_keywords  # Use the globally stored keywords from /extract_keywords
            matching_results = []

            for transcript in list_transcripts:
                if transcript['audio'] != 'input_audio':  # Exclude the input transcript
                    for keyword in keywords:
                        if keyword.lower() in transcript['transcript'].lower():
                            matching_results.append(
                                {'audio_file': transcript['audio'], 'transcript': transcript['transcript']})
                            break

            if not matching_results:
                response = "No matches found in any of these audios."
            else:
                response = matching_results

            return jsonify(response)

        except Exception as e:
            return jsonify({'error': str(e)})


    if __name__ == '__main__':
        app.run()
