import os
from dotenv import load_dotenv

# Load the environment variables from .env file
load_dotenv()

__configuration = {
    "Default": {
        "Documents":[
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\GenAI Summarization\\Analysis\\TextExractAndVectorization\\0_Final Ruling\\CY2025 OPPS Final Rule.pdf",
                "Name": "CY2024 OPPS Final Rule",
                "Description": "OPPS 2024 Final Rule"
            }
        ],
        "FactSheetLocation": "T:\\Data\\CMS\\Fee Schedules\\GenAI Summarization\\Analysis\\TextExractAndVectorization\\0_Final Ruling\\CY2025 OPPS Final Rule Fact Sheet.pdf",
        "ConvertToImagesFirst": True,
        "TempImageLocation": "C:\\src\\data\\extracted_images",
        "CleanupTempData": False,
        "StartingChunkCount": 0,
        "UseAIChunking": True,
        "PartitionKey": "OPPS_2025_FINAL_V2",
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
        "ChunkingCharacter":". ",
        "SpoolingSize": 50
    }
}

def get_config(key: str):
    environment_value = os.getenv(key)
    if environment_value != None:
        return environment_value
    value = __configuration["Default"][key] if key in __configuration["Default"] else None
    return value