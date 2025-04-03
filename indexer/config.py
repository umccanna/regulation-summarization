import os
from dotenv import load_dotenv

# Load the environment variables from .env file
load_dotenv()

__configuration = {
    "Default": {
        "Documents":[
            {
                "Location": "C:\\src\\data\\gen_ai_load\\HGBTechSpec\\AHEAD_CMS Medicare FFS HGB technical specifications 3.0_At-A-Glance_Pre-508.pdf",
                "Name": "AHEAD_CMS Medicare FFS HGB technical specifications 3.0_At-A-Glance_Pre-508",
                "Description": "At-A-Glance overview of the CMS designed Medicare FFS HGB Version 3.0 Methodology"
            },
            {
                "Location": "C:\\src\\data\\gen_ai_load\\HGBTechSpec\\AHEAD_CMS Medicare FFS HGB technical specifications 3.0_Pre-508.pdf",
                "Name": "AHEAD_CMS Medicare FFS HGB technical specifications 3.0_Pre-508",
                "Description": "Describes the financial methodology and operational payment features for Medicare FFS HGB under the AHEAD Model for Version 3.0"
            }
        ],
        "FactSheetLocation": None,
        "ConvertToImagesFirst": True,
        "TempImageLocation": "C:\\src\\data\\extracted_images",
        "CleanupTempData": False,
        "StartingChunkCount": 0,
        "UseAIChunking": True,
        "PartitionKey": "AHEAD_FFS_HGB_METHODOLOGY_3",
        "AZURE_OPENAI_ENDPOINT": "https://seattlehealth-openai.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "",
        "EmbeddingsModel": "seattlehealth-embeddings-small",
        "ChatModel": "seattlehealth-gpt-4o",
        "COSMOS_DB_URL": "https://seattlehealth-cdb-ai.documents.azure.com:443/",
        "COSMOS_DB_KEY": "",
        "DATABASE_NAME": "summarizations",
        "CONTAINER_NAME": "pricingregulations",
        "ChunkSize": 30,
        "Overlap": 3,
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