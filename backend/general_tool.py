import os
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

# Get API key
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Create the General chain
general_llm = ChatGoogleGenerativeAI(model="gemini-pro-latest", temperature=0.7, google_api_key=GOOGLE_API_KEY)
general_prompt_template = "{user_input}"
general_prompt = PromptTemplate.from_template(general_prompt_template)
general_chain = general_prompt | general_llm | StrOutputParser()

# --- Define the tool function ---

def ask_general_knowledge(user_input: str) -> str:
    """Answers general knowledge questions."""
    print("Tool: Calling General Knowledge")
    return general_chain.invoke(user_input)