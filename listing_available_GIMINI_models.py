import streamlit as st
import requests
from bs4 import BeautifulSoup
import PyPDF2
import docx2txt
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import os

def list_models():
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
    url = 'https://generativelanguage.googleapis.com/v1beta2/models'

    params = {
        'key': GEMINI_API_KEY
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        st.write("Available Models:", data)
        return data
    except requests.exceptions.RequestException as e:
        st.error(f"Error listing models: {e}")
        return None

def chat_with_gemini(user_input, context):
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
    
    if GEMINI_API_KEY is None:
        st.error("Please set the GEMINI_API_KEY environment variable or add it to Streamlit secrets.")
        return None

    # Set the actual Gemini API endpoint - adjust model name after listing
    url = 'https://generativelanguage.googleapis.com/v1beta2/models/gemini-1.5-flash-latest:generateText'

    headers = {
        'Content-Type': 'application/json',
    }

    params = {
        'key': GEMINI_API_KEY
    }

    payload = {
        'prompt': {
            'text': user_input + "\n" + context
        },
        'temperature': 0.7,
        'maxOutputTokens': 256
    }

    try:
        response = requests.post(url, headers=headers, params=params, json=payload)
        response.raise_for_status()
        data = response.json()
        assistant_response = data.get('candidates', [{}])[0].get('output', 'No response from Gemini API.')
        return assistant_response
    except requests.exceptions.HTTPError as errh:
        st.error(f"HTTP Error {response.status_code}: {response.text}")
    except requests.exceptions.ConnectionError as errc:
        st.error(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        st.error(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        st.error(f"An Error Occurred: {err}")
    return None



def main():
    st.title("Universal Content Chatbot with Gemini API")

    # List available models to find the correct model name
    models = list_models()
    
    if 'context' not in st.session_state:
        st.session_state['context'] = ''

    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    input_type = st.selectbox("Select input type:", ["File Upload", "URL", "YouTube Link"])

    if input_type == "File Upload":
        uploaded_file = st.file_uploader("Choose a file", type=['txt', 'pdf', 'docx'])
    elif input_type == "URL":
        url = st.text_input("Enter the URL")
    elif input_type == "YouTube Link":
        youtube_url = st.text_input("Enter the YouTube video link")

    if st.button("Process"):
        if input_type == "File Upload" and uploaded_file is not None:
            context = extract_text_from_file(uploaded_file)
        elif input_type == "URL" and url:
            context = extract_text_from_url(url)
        elif input_type == "YouTube Link" and youtube_url:
            context = extract_text_from_youtube(youtube_url)
        else:
            st.error("Please provide valid input.")
            return

        if context:
            st.session_state['context'] = context
            st.session_state['chat_history'] = []
            st.success("Content extracted successfully!")
        else:
            st.error("Failed to extract content.")

    if st.session_state.get('context', ''):
        st.subheader("Chat with the Content")
        user_input = st.text_input("You:", key="user_input")
        if user_input:
            assistant_response = chat_with_gemini(user_input, st.session_state['context'])
            if assistant_response:
                # Save the conversation history
                st.session_state['chat_history'].append((user_input, assistant_response))

                # Display the conversation
                for i, (user_msg, assistant_msg) in enumerate(st.session_state['chat_history']):
                    st.markdown(f"**You:** {user_msg}")
                    st.markdown(f"**Assistant:** {assistant_msg}")
            else:
                st.error("Failed to get a response from the Gemini API.")

if __name__ == "__main__":
    main()




#
import streamlit as st
import requests
from bs4 import BeautifulSoup
import PyPDF2
import docx2txt
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

# Extract text from files
def extract_text_from_file(uploaded_file):
    if uploaded_file is not None:
        file_type = uploaded_file.type
        if file_type == "application/pdf":
            return extract_text_from_pdf(uploaded_file)
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return extract_text_from_docx(uploaded_file)
        elif file_type == "text/plain":
            return str(uploaded_file.read(), "utf-8")
        else:
            st.error("Unsupported file type.")
    return None

def extract_text_from_pdf(pdf_file):
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF file: {e}")
        return None

def extract_text_from_docx(docx_file):
    try:
        text = docx2txt.process(docx_file)
        return text
    except Exception as e:
        st.error(f"Error reading DOCX file: {e}")
        return None

# Extract text from URL
def extract_text_from_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        # Remove scripts and styles
        for element in soup(["script", "style"]):
            element.extract()
        text = soup.get_text(separator=' ')
        return text
    except Exception as e:
        st.error(f"Error fetching URL content: {e}")
        return None

# Extract text from YouTube video
def extract_text_from_youtube(youtube_url):
    def get_video_id(url):
        query = urlparse(url)
        if query.hostname == 'youtu.be':
            return query.path[1:]
        elif query.hostname in ('www.youtube.com', 'youtube.com'):
            if query.path == '/watch':
                return parse_qs(query.query).get('v', [None])[0]
            elif query.path[:7] == '/embed/':
                return query.path.split('/')[2]
            elif query.path[:3] == '/v/':
                return query.path.split('/')[2]
        return None

    video_id = get_video_id(youtube_url)
    if video_id:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = None
            try:
                transcript = transcript_list.find_transcript(['en', 'en-US'])
            except:
                transcript = transcript_list.find_generated_transcript(transcript_list._manually_created_transcripts or transcript_list._generated_transcripts)

            if transcript:
                text = ' '.join([t['text'] for t in transcript.fetch()])
                return text
            else:
                st.error("No transcript available for this video.")
                return None
        except Exception as e:
            st.error(f"Error fetching transcript: {e}")
            return None
    else:
        st.error("Invalid YouTube URL")
        return None

# Chat with the Gemini API
def chat_with_gemini(user_input, context):
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
    if GEMINI_API_KEY is None:
        st.error("Please set the GEMINI_API_KEY environment variable or add it to Streamlit secrets.")
        return None

    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}'
    headers = {'Content-Type': 'application/json'}
    payload = {
        'contents': [
            {
                'parts': [
                    {
                        'text': f"{context}\n\n{user_input}"
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        assistant_response = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No response from Gemini API.')
        return assistant_response
    except requests.exceptions.HTTPError as errh:
        st.error(f"HTTP Error {response.status_code}: {response.text}")
    except requests.exceptions.ConnectionError as errc:
        st.error(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        st.error(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        st.error(f"An Error Occurred: {err}")
    return None

# Streamlit App
def main():
    st.title("Multi-Input RAG Chatbot with Gemini API")
    st.write("Upload a file, paste a URL, or enter a YouTube link to chat with its content.")

    if 'context' not in st.session_state:
        st.session_state['context'] = ''

    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    input_type = st.selectbox("Select input type:", ["File Upload", "URL", "YouTube Link"])

    if input_type == "File Upload":
        uploaded_file = st.file_uploader("Choose a file", type=['txt', 'pdf', 'docx'])
    elif input_type == "URL":
        url = st.text_input("Enter the URL")
    elif input_type == "YouTube Link":
        youtube_url = st.text_input("Enter the YouTube video link")

    if st.button("Process"):
        if input_type == "File Upload" and uploaded_file is not None:
            context = extract_text_from_file(uploaded_file)
        elif input_type == "URL" and url:
            context = extract_text_from_url(url)
        elif input_type == "YouTube Link" and youtube_url:
            context = extract_text_from_youtube(youtube_url)
        else:
            st.error("Please provide valid input.")
            return

        if context:
            st.session_state['context'] = context
            st.session_state['chat_history'] = []
            st.success("Content extracted successfully!")
        else:
            st.error("Failed to extract content.")

    if st.session_state.get('context', ''):
        st.subheader("Chat with the Content")
        user_input = st.text_input("You:", key="user_input")
        if user_input:
            assistant_response = chat_with_gemini(user_input, st.session_state['context'])
            if assistant_response:
                st.session_state['chat_history'].append((user_input, assistant_response))
                for user_msg, assistant_msg in st.session_state['chat_history']:
                    st.markdown(f"**You:** {user_msg}")
                    st.markdown(f"**Assistant:** {assistant_msg}")
            else:
                st.error("Failed to get a response from the Gemini API.")

if __name__ == "__main__":
    main()


#