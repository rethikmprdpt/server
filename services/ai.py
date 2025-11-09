import google.generativeai as genai  # noqa: INP001
from fastapi import HTTPException, status

from schemas.chat import ChatRequest
from utils.auth import settings  # <-- Import your settings

# --- 1. Configure the Gemini Client ---
# This happens once when the file is loaded.
# It securely reads the key from your .env file via the Settings object.
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
except Exception as e:  # noqa: BLE001
    print(f"CRITICAL: Failed to configure Gemini API. Is GEMINI_API_KEY set? {e}")

# --- 2. Define the System Prompt ---
# This is the same prompt from your old JS file
system_prompt = """
You are a friendly and professional AI assistant for a network technician. 
Your name is "Tech Assist."
Your primary job is to answer the technician's questions about the current installation task.
**YOUR RULES:**
1.  You will be given the task's data as a JSON object under the "TASK DATA" heading.
2.  You MUST base your answers *only* on the provided "TASK DATA" JSON.
3.  DO NOT make up information. If the answer is not in the JSON, politely say "I do not have that information in the task details."
4.  Be concise and helpful. Format technical details (like serial numbers) clearly.
5.  You also have knowledge of the 3-step installation checklist, which is:
    * Step 1: "Test fiber signal from splitter port"
    * Step 2: "Connect ONT and check power/light"
    * Step 3: "Connect router and test LAN/WiFi signal"
    You can answer general questions about these 3 steps.
"""


# --- 3. The Main Service Function ---
async def get_gemini_response(chat_request: ChatRequest) -> str:
    try:
        # 1. Select the model
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-preview-09-2025",
            system_instruction=system_prompt,
        )

        # 2. Format the user's new message with context
        user_message_with_context = f"""
---
TASK DATA:
{chat_request.task_context}
---

USER QUESTION:
{chat_request.new_question}
        """

        # 3. Build the final history to send
        # The history from the client + the new user message
        history_as_dicts = [part.model_dump() for part in chat_request.chat_history]

        # Now, api_history is a clean list[dict]
        api_history = [
            *history_as_dicts,
            {"role": "user", "parts": [{"text": user_message_with_context}]},
        ]
        # 4. Start the chat session
        # We pass in the *previous* history to continue the conversation
        chat = model.start_chat(
            history=api_history[:-1],  # type: ignore[arg-type]
        )  # Pass all *except* the new message

        # 5. Send the new message
        # We use await for the async call
        response = await chat.send_message_async(api_history[-1]["parts"])

    except Exception as e:  # noqa: BLE001
        print(f"Error in Gemini service: {e}")
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while contacting the AI assistant: {e}",
        )
    else:
        return response.text
