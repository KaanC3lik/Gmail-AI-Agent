from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import List, TypedDict, Optional
from pydantic import BaseModel, Field

from dotenv import load_dotenv
load_dotenv()  # This loads variables from .env into environment

# --- Environment Setup ---
# Make sure to set your GOOGLE_API_KEY environment variable
# os.environ["GOOGLE_API_KEY"] = "YOUR_API_KEY"

class Mail(BaseModel):
    """You will receive mail history from clients. Respond with Mail structure"""

    subject: str = Field(description="Subject of the mail")
    mail_body: str = Field(description="The body to the Mail")

def process_email(email_sender, email_history):
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")
    structured_llm = llm.with_structured_output(Mail)

    initial_prompt = f"""
    Answer clients quesiton or solve their problems.Here is the recent email history with {email_sender}:
    ---
    {" ".join(email_history)}
    """

    response = structured_llm.invoke([HumanMessage(content=initial_prompt)])

    return (response.subject, response.mail_body)


# --- Example Usage ---
if __name__ == "__main__":
    sender_email = "test@example.com"
    history = [
        "Subject: Project Update\nHi Team, the project is on track.\n",
        "Subject: Re: Project Update\nThanks for the update! Any blockers?\n"
    ]
    print(process_email(sender_email, history))
