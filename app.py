from flask import Flask, request, render_template, redirect, url_for, jsonify
import os, logging, re
from dotenv import load_dotenv
import google.generativeai as genai
from elevenlabs import ElevenLabs

load_dotenv()

app = Flask(__name__)

# Secret key for session management
app.secret_key = os.urandom(24)

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,  # Change to DEBUG to get more detailed logs
    format='%(asctime)s %(levelname)s %(message)s',
)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ELEVEN_LABS_API_KEY = os.getenv('ELEVEN_LABS_API_KEY')

# @app.route('/', methods=['GET', 'POST'])
# def index():
#     if request.method == 'POST':
#         text_input = request.form.get('text_input')

#         if not text_input:
#             return render_template('index.html', error='Please enter some text')
        
#         try:
#             # Generate conversation
#             conversation_text = generate_conversation(text_input)
            
#             # Generate audio file
#             audio_file = generate_audio(conversation_text)
            
#             # Render template with audio playback
#             return render_template('index.html', audio_file=audio_file, conversation_text=conversation_text)
        
#         except Exception as e:
#             error_message = f"An error occurred: {str(e)}"
#             return render_template('index.html', error=error_message)

    # return render_template('index.html')

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    text_input = request.form.get('text_input')

    if not text_input:
        return jsonify({'error': 'Please enter some text'}), 400
    
    try:
        # Generate conversation
        conversation_text = generate_conversation(text_input)
        
        # Generate audio file
        audio_file = generate_audio(conversation_text)
        
        # Return JSON response with paths
        return jsonify({
            'conversation_text': conversation_text,
            'audio_file': url_for('static', filename='audio/conversation.mp3')
        })
    
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return jsonify({'error': error_message}), 500
    
def generate_conversation(text_input):
    logging.debug("Starting conversation generation.")
    prompt = (
        "Create a conversational dialogue between two people (Person A and Person B)"
        "in a podcast style discussing the following content:\n\n"
        f"{text_input}\n\n"
        "The conversation should be natural, engaging, and cover key points from the text.\n"
        "Please format the conversation as follows:\n"
        "Speaker: Text\n"
        "Avoid including any introductions, conclusions, or annotations.\n"
        "Only include the dialogue between Person A and Person B.\n"
        "Add emotions and expressions to make the conversation more engaging.\n"
        "Add small talk, jokes, or personal anecdotes to make the conversation more engaging.\n"
        "Its not necessary to have entire sentences every time we can go back and forth with just a few words.\n"
        "Such as:\n"
        "ohh, damn, really, hmm, interesting, etc.\n"
        "these kind of small touches make the conversation feel real.\n"
    )
    # Configure the Gemini API with the API key
    genai.configure(api_key=GEMINI_API_KEY)

    # Define generation configuration
    generation_config = {
        "temperature": 1,
        # "top_p": 0.95,
        # "top_k": 64,
        # "max_output_tokens": 32769,
        "max_output_tokens": 32768,
        "response_mime_type": "text/plain",
    }

    # Initialize the Gemini generative model
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro-002",
        generation_config=generation_config,
        # Uncomment and configure safety settings if needed
        # safety_settings = Adjust safety settings
        # See https://ai.google.dev/gemini-api/docs/safety-settings
    )

    # Start a chat session with an empty history
    chat_session = model.start_chat(history=[])

    try:
        response = chat_session.send_message(prompt)
        logging.debug("Conversation generation completed.")
        return response.text
    except Exception as e:
        logging.error(f"An error occurred during conversation generation: {str(e)}")
        raise Exception(f"An error occurred during conversation generation: {str(e)}")
    

def generate_audio(conversation_text):
    # Initialize Eleven Labs client
    client = ElevenLabs(
        api_key=ELEVEN_LABS_API_KEY,
    )

    # Split conversation into lines
    lines = conversation_text.strip().split('\n')

    # Define voice mappings
    voice_mappings = {
        'Host': '9BWtsMINqrJLrRacOk9x',
        'Person A': '9BWtsMINqrJLrRacOk9x',
        'Person B': 'FGY2WhTYpPnrIDTdsKH5',
        '[Person B\'s name]': 'FGY2WhTYpPnrIDTdsKH5',
        # Add any other variations that may occur
    }

    # Initialize variables
    audio_segments = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith('**('):
            logging.debug(f"Skipping line: {line}")
            continue

        # Use regex to extract speaker and spoken text
        match = re.match(r'^\*\*(.*?)\*\*:\s*(.*)', line)  # Matches **Speaker**: Text
        if not match:
            match = re.match(r'^(.*?)[:：]\s*(.*)', line)  # Matches Speaker: Text
        if match:
            speaker = match.group(1).strip()
            spoken_text = match.group(2).strip()
            logging.debug(f"Speaker: {speaker}, Text: {spoken_text}")
        else:
            logging.debug(f"Could not parse line: {line}")
            continue

        # Map the speaker to a voice
        current_voice = voice_mappings.get(speaker, 'Bex')  # Default to 'Bex' if speaker not found

        # Generate speech
        try:
            audio_generator = client.generate(
                text=spoken_text,
                voice=current_voice,
                model='eleven_monolingual_v1',
                stream=True,
            )
            # Read bytes from the generator and collect them
            audio_bytes = b''.join(audio_generator)
            audio_segments.append(audio_bytes)
        except Exception as e:
            logging.error(f"An error occurred during audio generation for line '{line}': {str(e)}")
            raise Exception(f"An error occurred during audio generation: {str(e)}")

    if not audio_segments:
        raise Exception("No audio segments were generated. Please check the conversation text.")

    # Combine audio segments
    combined_audio = b''.join(audio_segments)

    # Save the combined audio to a file
    audio_file_path = os.path.join('static', 'audio', 'conversation.mp3')
    os.makedirs(os.path.dirname(audio_file_path), exist_ok=True)
    with open(audio_file_path, 'wb') as f:
        f.write(combined_audio)

    return audio_file_path


if __name__ == '__main__':
    app.run(debug=True)