from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import openai
import json
from pydantic import BaseModel

app = FastAPI()

# ✅ Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to ["http://localhost:3000"] for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Replace with your OpenAI API Key (DO NOT hardcode in production)
OPENAI_API_KEY = "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"

# ✅ OpenAI API client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ✅ Store chat history per session (basic in-memory storage for now)
chat_sessions = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str

def parse_zap_report(file_content):
    """
    Parses the OWASP ZAP JSON report and extracts vulnerabilities.
    """
    try:
        report_data = json.loads(file_content.decode("utf-8"))
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format. Ensure the ZAP scan report is valid.")

    vulnerabilities = []

    if isinstance(report_data, dict) and "site" in report_data:
        for site in report_data["site"]:
            if isinstance(site, dict):
                for alert in site.get("alerts", []):
                    if isinstance(alert, dict):
                        vulnerabilities.append({
                            "name": alert.get("name", "Unknown Vulnerability"),
                            "risk": alert.get("risk", "Unknown Risk"),
                            "description": alert.get("description", "No description available"),
                            "solution": alert.get("solution", "No solution available"),
                            "reference": alert.get("reference", "No reference provided")
                        })

    return vulnerabilities

def analyze_with_gpt(vulnerabilities):
    """
    Sends vulnerability details to OpenAI's GPT-4o and gets an analysis.
    """
    prompt = "You are a cybersecurity expert. Analyze the following OWASP ZAP vulnerabilities and suggest fixes:\n\n"

    for vuln in vulnerabilities:
        prompt += f"Vulnerability: {vuln['name']}\n"
        prompt += f"Risk Level: {vuln['risk']}\n"
        prompt += f"Description: {vuln['description']}\n"
        prompt += f"Solution: {vuln['solution']}\n"
        prompt += f"Reference: {vuln['reference']}\n\n"

    prompt += "Provide clear, step-by-step fixes for each vulnerability."

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}]
    )

    return response.choices[0].message.content

@app.post("/upload/")
async def upload_zap_report(file: UploadFile = File(...)):
    """
    Handles file upload, extracts vulnerabilities, and initializes chat history.
    """
    content = await file.read()
    try:
        vulnerabilities = parse_zap_report(content)
        chat_analysis = analyze_with_gpt(vulnerabilities)

        # Initialize chat session
        session_id = "user_session"  # In a real app, use a unique user/session ID
        chat_sessions[session_id] = [
            {"role": "system", "content": "This is a ZAP security analysis chatbot. Ask me about vulnerabilities."},
            {"role": "assistant", "content": chat_analysis}
        ]

        return {"session_id": session_id, "vulnerabilities": vulnerabilities, "analysis": chat_analysis}
    except Exception as e:
        return {"error": str(e)}

@app.post("/chat/")
async def chat_with_gpt(request: ChatRequest):
    """
    Handles chatbot conversations, maintains context, and responds to user queries.
    """
    session_id = request.session_id
    message = request.message

    if session_id not in chat_sessions:
        return {"error": "Session not found. Please upload a ZAP scan first."}

    # Append user message to chat history
    chat_sessions[session_id].append({"role": "user", "content": message})

    # Call GPT-4o with chat history for context
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=chat_sessions[session_id]
    )

    bot_response = response.choices[0].message.content

    # Append bot response to chat history
    chat_sessions[session_id].append({"role": "assistant", "content": bot_response})

    return {"response": bot_response}