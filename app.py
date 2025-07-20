from flask import Flask, request, jsonify
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import os

app = Flask(__name__)

# load .env file
load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def extract_video_id(youtube_url):
    parsed_url = urlparse(youtube_url)
    if parsed_url.hostname in ['youtu.be']:
        return parsed_url.path[1:]
    elif parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query)['v'][0]
    raise ValueError("Invalid YouTube URL")

def fetch_transcript(video_url):
    video_id = extract_video_id(video_url)

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        try:
            transcript = transcript_list.find_transcript(['en'])
        except NoTranscriptFound:
            transcript = transcript_list.find_transcript(['hi'])

        fetched_transcript = transcript.fetch()
        full_text = " ".join([entry.text for entry in fetched_transcript])
        return full_text

    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return ""

def generate_mcqs(transcript_text, num_questions=10):
    prompt = f"""
You are an AI assistant designed to generate high-quality, professional multiple-choice questions (MCQs) from educational video content.

Your task is to:
- Understand the core concepts from the transcript of a YouTube video.
- Generate concept-based MCQs suitable for undergraduate-level Computer Science students.
- Avoid referring to the transcript directly (e.g., do not use "according to the transcript" or "according to the text" or “according to the video” or “as stated above”).
- Make questions sound natural and exam-ready.

Each question must:
- Be clear and technically accurate.
- Have exactly one correct answer and three related but wrong distractions.
- Target medium-difficulty level.
- Be based on topics typically found in BTech CSE, such as programming, data structures, algorithms, machine learning, and academic subjects also like engineering physics, engineering mathematics, engineering chemistry, fundamentals of electronics and electrical etc.

---

Here are some example questions for reference:

Example 1:
1. What is the time complexity of inserting an element into a max-heap?
    A. O(log n)  
    B. O(1)  
    C. O(n log n)  
    D. O(n²)  
Answer: A

Example 2:
2. Which of the following is NOT a valid use-case for a hash table?
    A. Implementing a dictionary  
    B. Storing hierarchical data like XML  
    C. Caching data  
    D. Checking for duplicates in a list  
Answer: B

Example 3:
3. In supervised learning, which of the following best defines the "training dataset"?
    A. A dataset used only to test the model’s performance  
    B. A dataset containing input-output pairs used to teach the model  
    C. A dataset with only input features and no labels  
    D. A dataset created from real-time user interactions  
Answer: B

---

Now, generate 10 MCQs based on the following transcript:

Transcript:
\"\"\"
{transcript_text}
\"\"\"

Output format:
1. Question?
    A. Option1
    B. Option2
    C. Option3
    D. Option4
Answer: A
"""

    try:
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating MCQs: {e}")
        return ""

@app.route("/generate-quiz", methods=["POST"])
def generate_quiz():
    data = request.json
    video_url = data.get("video_url")

    if not video_url:
        return jsonify({"error": "video_url is required"}), 400

    transcript = fetch_transcript(video_url)
    if not transcript:
        return jsonify({"error": "Could not fetch transcript"}), 500

    mcqs_text = generate_mcqs(transcript)
    if not mcqs_text:
        return jsonify({"error": "Failed to generate MCQs"}), 500

    return jsonify({"quiz": mcqs_text})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
