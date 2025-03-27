import os
from dotenv import load_dotenv

# Load the environment variables from .env file
load_dotenv()

__configuration = {
    "Default": {
        "FactSheetLocation": "T:\\Data\\CMS\\Fee Schedules\\GenAI Summarization\\Analysis\\TextExractAndVectorization\\0_Final Ruling\\CY2024 OPPS Final Rule Fact Sheet.pdf",
        "FinalRuleLocation": "T:\\Data\\CMS\\Fee Schedules\\GenAI Summarization\\Analysis\\TextExractAndVectorization\\0_Final Ruling\\CY2024 OPPS Final Rule.pdf",
        "Year": 2024,
        "Model": "PROF",
        "AZURE_OPENAI_ENDPOINT": "https://seattlehealth-openai.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "",
        "EmbeddingsModel": "seattlehealth-embeddings-small",
        "SummarizingModel": "seattlehealth-gpt-4o-mini-default",
        "ChatModel": "seattlehealth-gpt-4o",
        "COSMOS_DB_URL": "https://seattlehealth-cdb-ai.documents.azure.com:443/",
        "COSMOS_DB_KEY": "",
        "DATABASE_NAME": "summarizations",
        "CONTAINER_NAME": "pricingregulations",
        "Okta__Audience": "0oa1uj3zlj5hatOW91d8",
        "Okta__Issuer": "https://milliman.okta.com",
        "ChunkSize": 20,
        "Overlap": 5,
        "ChunkingCharacter":".",
        "SpoolingSize": 50
    }
}

def get_config(key: str):
    environment_value = os.getenv(key)
    if environment_value != None:
        return environment_value
    value = __configuration["Default"][key] if key in __configuration["Default"] else None
    return value