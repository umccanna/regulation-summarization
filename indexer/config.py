import os
from dotenv import load_dotenv

# Load the environment variables from .env file
load_dotenv()

__configuration = {
    "Default": {
        "Documents":[
    {
        "Location": "T:\\Data\\CMS\\Fee Schedules\\2026\\RBRVS\\Data\\2025-13271.pdf",
        "Name": "T:\\Data\\CMS\\Fee Schedules\\2026\\RBRVS\\Data\\2025-13271.pdf",
        "Description": "Prof 2026 Proposed CMS Pricing Rules"
    }
    #,
    # {
    #     "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\Vermont\\VT Global Payment Program Methods and Specs_20240708.pdf",
    #     "Name": "VT Global Payment Program Methods and Specs_20240708",
    #     "Description": "VT Global Payment Program Methods and Specs_20240708"
    # },
    # {
    #     "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\Vermont\\2024.12.16 Draft Vermont AHEAD State Agreement_for website.pdf",
    #     "Name": "2024.12.16 Draft Vermont AHEAD State Agreement_for website",
    #     "Description": "2024.12.16 Draft Vermont AHEAD State Agreement_for website"
    # }
    # ,
    # {
    #     "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\Maryland\\MD AHEAD Application FINAL PUBLIC 03152024.pdf",
    #     "Name": "MD AHEAD Application FINAL PUBLIC 03152024",
    #     "Description": "MD AHEAD Application FINAL PUBLIC 03152024"
    # },
    # {
    #     "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\Maryland\\Final MD AHEAD State Agreement_102824.pdf",
    #     "Name": "Final MD AHEAD State Agreement_102824",
    #     "Description": "Final MD AHEAD State Agreement_102824"
    # }
    # #,
    # {
    #     "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\New York\\ahead_model_project_narrative.pdf",
    #     "Name": "ahead_model_project_narrative",
    #     "Description": "ahead_model_project_narrative"
    # },
    # {
    #     "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\Connecticut\\ct-ahead-application.pdf",
    #     "Name": "ct-ahead-application",
    #     "Description": "ct-ahead-application"
    # },
    # {
    #     "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\Rhode Island\\RI AHEAD State Agreement 1.16.2025 RI signed_CMS signed Fully Executed.pdf",
    #     "Name": "RI AHEAD State Agreement 1.16.2025 RI signed_CMS signed Fully Executed",
    #     "Description": "RI AHEAD State Agreement 1.16.2025 RI signed_CMS signed Fully Executed"
    # },
    # {
    #     "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\Data from client\\20241219 AHEAD Application\\2nd Round V2 Revised Project Narrative 052224 for Milliman.pdf",
    #     "Name": "2nd Round V2 Revised Project Narrative 052224 for Milliman",
    #     "Description": "2nd Round V2 Revised Project Narrative 052224 for Milliman"
    # }
        ],
        "FactSheetLocation": "T:\\Data\\CMS\\Fee Schedules\\2026\\RBRVS\\Data\\Calendar Year (CY) 2026 Medicare Physician Fee Schedule (PFS) Proposed Rule (CMS-1832-P) _ CMS.pdf",
        "ConvertToImagesFirst": True,
        "TempImageLocation": "C:\\src\\data\\extracted_images",
        "CleanupTempData": False,
        "StartingChunkCount": 0,
        "UseAIChunking": True,
        "PartitionKey": "PROF_2026_PROPOSED",
        "AZURE_OPENAI_ENDPOINT": "https://seattlehealth-openai.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "",
        "EmbeddingsModel": "seattlehealth-embeddings-small",
        "ChatModel": "gpt-4.1-mini",
        "COSMOS_DB_URL": "https://seattlehealth-cdb-ai.documents.azure.com:443/",
        "COSMOS_DB_KEY": "",
        "DATABASE_NAME": "summarizations",
        "CONTAINER_NAME": "pricingregulations",
        "ChunkSize": 5,
        "Overlap": 2,
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