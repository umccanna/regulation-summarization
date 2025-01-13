import os
from dotenv import load_dotenv

# Load the environment variables from .env file
load_dotenv()

__configuration = {
    "Default": {
        "FactSheetLocation": "T:\\Data\\CMS\\Fee Schedules\\2025\\RBRVS\\Data\\01 - Final Rule\\Calendar Year (CY) 2025 Medicare Physician Fee Schedule Final Rule _ CMS.pdf",
        "FinalRuleLocation": "T:\\Data\\CMS\\Fee Schedules\\2025\\RBRVS\Data\\01 - Final Rule\\2024-25382.pdf",
        #"FactSheetLocation": "T:\\Data\\CMS\\Fee Schedules\\2024\\OPPS\\Data\\01 - Final Rule\\CY2024 OPPS Final Rule Fact Sheet.pdf",
        #"FinalRuleLocation": "T:\\Data\\CMS\\Fee Schedules\\2024\\OPPS\\Data\\01 - Final Rule\\CY2024 OPPS Final Rule.pdf",
        #"FactSheetLocation": "T:\\Data\\CMS\\Fee Schedules\\2025\\OPPS\\Data\\01 - Final Rule\\CY2025 OPPS Final Rule Fact Sheet.pdf",
        #"FinalRuleLocation": "T:\\Data\\CMS\\Fee Schedules\\2025\\OPPS\\Data\\01 - Final Rule\\CY2025 OPPS Final Rule.pdf",
        "Year": 2024,
        "Model": "Prof",
        "AZURE_OPENAI_ENDPOINT": "https://seattlehealth-openai.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "",
        "EmbeddingsModel": "seattlehealth-embeddings-small",
        "ChatModel": "seattlehealth-gpt-4o",
        "COSMOS_DB_URL": "https://seattlehealth-cdb-ai.documents.azure.com:443/",
        "COSMOS_DB_KEY": "",
        "DATABASE_NAME": "summarizations",
        "CONTAINER_NAME": "pricingregulations",
        "ChunkSize": 30,
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