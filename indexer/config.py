import os
from dotenv import load_dotenv

# Load the environment variables from .env file
load_dotenv()

__configuration = {
    "Default": {
        "Documents":[
            {
                "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\Rhode Island\\RI AHEAD State Agreement 1.16.2025 RI signed_CMS signed Fully Executed.pdf",
                "Name": "RI AHEAD State Agreement 1.16.2025 RI signed_CMS signed Fully Executed",
                "Description": "Rhode Island AHEAD State Agreement"
            }
        ],
        "ConvertToImagesFirst": True,
        "TempImageLocation": "C:\\src\\data\\extracted_images",
        "CleanupTempData": False,
        "StartingChunkCount": 289,
        "UseAIChunking": True,
        "PartitionKey": "AHEAD_NOFO_ALL_STATE_NARRATIVES",
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