import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()

class Llm_connection():

    def __init__(self,llm_model='openai'):

        self.llm_model = llm_model
        self.key = os.getenv(llm_model)
        
        print(f"DEBUG: GOOGLE_API_KEY lida: {'*' * (len(self.key) - 5)}{self.key[-5:]}") 
    
    def connection(self):

        if self.llm_model == 'gemini':
            # return "gemini/gemini-1.5-flash" 
            os.environ["GOOGLE_API_KEY"] = self.key
            return ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=self.key)
        elif self.llm_model == 'openai':
            os.environ['OPENAI_MODEL_NAME'] = 'gpt-4o'
            os.environ['OPENAI_API_BASE'] = 'https://api.openai.com/v1'
            os.environ['OPENAI_API_KEY'] = self.key

            

    