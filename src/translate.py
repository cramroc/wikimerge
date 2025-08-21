# imports
import os
from dotenv import load_dotenv

# Translator
class DeepLTranslator:
    def __init__(self):
        load_dotenv() # look for .env in project root
        api_key = os.getenv("DEEPL_API_KEY") # get api key from .env
        if not api_key: # check api_key is not empty
            raise RuntimeError(
                "DEEPL_API_KEY is missing. Add it to your .env file."
            )
        self.api_key = api_key # assign api key to translator
