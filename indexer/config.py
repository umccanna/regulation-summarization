import os
from dotenv import load_dotenv

# Load the environment variables from .env file
load_dotenv()

__configuration = {
    "Default": {
        "Documents":[
            {
                "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\CMS\\AHEAD-FinancialSpecsFFSHGBM_7_22_24.pdf",
                "Name": "AHEAD-FinancialSpecsFFSHGBM_7_22_24",
                "Description": "AHEAD Financial Specifications for the CMS-Designed Medicare FFS Hospital Global Budget Methodology"
            }
            #,
            # {
            #     "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\CMS\\AHEAD NOFO Final 11.15.2023 508.pdf",
            #     "Name": "AHEAD NOFO Final 11.15.2023 508",
            #     "Description": "AHEAD NOFO Final 2023"
            # } 
        ],
        "FactSheetLocation": "T:\\Data\\CMS\\Fee Schedules\\GenAI Summarization\\Analysis\\TextExractAndVectorization\\0_Final Ruling\\CY2025 OPPS Final Rule Fact Sheet.pdf",
        "ConvertToImagesFirst": True,
        "TempImageLocation": "C:\\src\\data\\extracted_images",
        "CleanupTempData": False,
        "StartingChunkCount": 0,
        "UseAIChunking": True,
        "RemoveNewlinesDuringNormalization": False,
        "PartitionKey": "AHEAD_2023_FIN_SPECS",
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