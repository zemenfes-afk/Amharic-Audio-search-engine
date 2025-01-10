from pocketsphinx import pocketsphinx
from pydub import AudioSegment
import os
import glob

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
    config.set_string('-topn', '1')  # Set -topn to be <= the number of density codewords

    decoder = pocketsphinx.Decoder(config)

    # Load the converted audio file
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
    # Define a list of common stopwords to exclude from keywords
    stopwords = ['እና', 'እስከ', 'ወደ', 'ስለ', 'ግን', 'እንዲሁም', 'ለ', 'በ', 'የ', 'ከ']
    # Convert the transcript to lowercase and split it into individual words
    words = transcript.lower().split()
    # Remove stopwords and punctuation from the words
    cleaned_words = [word.strip('.,?!') for word in words if word not in stopwords]
    # Count the occurrences of each word
    word_counts = {}
    for word in cleaned_words:
        if word in word_counts:
            word_counts[word] += 1
        else:
            word_counts[word] = 1

    # Sort the words based on their occurrence count in descending order
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)

    # Extract the top keywords with the highest occurrence counts
    top_keywords = [word for word, count in sorted_words[:10]]  # Change 10 to the desired number of keywords

    # If more than 10 keywords, limit to the top 5
    if len(top_keywords) >= 10:
        top_keywords = top_keywords[:5]

    return top_keywords


def search_transcripts(audio_files, keyword_file):
    matches = []
    with open(keyword_file, 'r', encoding='utf-8') as file:
        keywords_str = file.read().strip()
    keywords = [keyword.strip() for keyword in keywords_str.split(',')]

    for audio_file in audio_files:
        transcript = transcribe_audio(audio_file, acoustic_model_path, language_model_path, phonetic_dictionary_path)
        for keyword in keywords:
            if transcript and keyword.lower() in transcript.lower():
                matches.append((audio_file, transcript))
                break  # Break out of the loop if any keyword is found in the transcript
    return matches


# Set the paths to your custom models and dictionary
acoustic_model_path = r'C:\CMU\Amharic1\output\Amharic.ci_cont'
language_model_path = r'C:\CMU\Amharic1\output\Amharic.lm.DMP'
phonetic_dictionary_path = r'C:\CMU\Amharic1\output\Amharic.dic'

# Convert and transcribe the first input audio
input_audio = r'C:\CMU\Amharic1\search\MWCone4.wav'
converted_audio = os.path.splitext(input_audio)[0] + '.wav'
convert_to_wav(input_audio, converted_audio)
transcript = transcribe_audio(converted_audio, acoustic_model_path, language_model_path, phonetic_dictionary_path)
keywords = extract_keywords(transcript)

# Generate the keyword file for the input audio
keyword_file = os.path.splitext(input_audio)[0] + '.txt'
with open(keyword_file, 'w', encoding='utf-8') as file:
    file.write(','.join(keywords))
    print("Keywords:", ", ".join(keywords))
    print("Transcript: " + transcript + "\n")
# Specify the audio folder path
audio_folder = r'C:\CMU\Amharic1\list'

# Specify the pattern to match all audio files
audio_file_pattern = os.path.join(audio_folder, '*')
# Retrieve a list of audio files in the folder
audio_files = glob.glob(audio_file_pattern)

# Perform search in the transcripts using the generated keywords
matching_results = search_transcripts(audio_files, keyword_file)
for audio_file, transcript in matching_results:
    print("Match found in:", audio_file)
    print("Transcript:", transcript)

if not matching_results:
    print("No matches found in any of these audios.")
