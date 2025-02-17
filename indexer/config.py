import os
from dotenv import load_dotenv

# Load the environment variables from .env file
load_dotenv()

__configuration = {
    "Default": {
        "Documents":[
            # {
            #     "Location": "C:\\src\\data\\pdf-to-onenote\\AHEAD NOFO Final 11.15.2023 508.pdf",
            #     "Name": "AHEAD NOFO Final 11.15.2023 508",
            #     "Description": "AHEAD NOFO Final Outline"
            # },
            {
                "Location": "C:\\src\\data\\pdf-to-onenote\\2nd Round V2 Revised Project Narrative 052224 for Milliman.pdf",
                "Name": "2nd Round V2 Revised Project Narrative 052224 for Milliman",
                "Description": "Hawaii's AHEAD project narrative that was provided to Milliman"
            },
            {
                "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\Vermont\\VT AHEAD Application Project Narrative.pdf",
                "Name": "VT AHEAD Application Project Narrative",
                "Description": "Vermont's AHEAD project narrative that was provided to Milliman"
            },
            {
                "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\Vermont\\VT Global Payment Program Methods and Specs_20240708.pdf",
                "Name": "VT Global Payment Program Methods and Specs_20240708",
                "Description": "Vermont's global payment program methods and specs"
            },
            {
                "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\Vermont\\2024.12.16 Draft Vermont AHEAD State Agreement_for website.pdf",
                "Name": "2024.12.16 Draft Vermont AHEAD State Agreement_for website",
                "Description": "Vermont's draft AHEAD state agreement"
            },
            {
                "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\Maryland\\MD AHEAD Application FINAL PUBLIC 03152024.pdf",
                "Name": "MD AHEAD Application FINAL PUBLIC 03152024",
                "Description": "Maryland's AHEAD application"
            },
            {
                "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\Maryland\\Final MD AHEAD State Agreement_102824.pdf",
                "Name": "Final MD AHEAD State Agreement_102824",
                "Description": "Maryland's AHEAD state agreement"
            },
            {
                "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\New York\\ahead_model_project_narrative.pdf",
                "Name": "ahead_model_project_narrative",
                "Description": "New York's AHEAD project narrative"
            },
            {
                "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\Connecticut\\ct-ahead-application.pdf",
                "Name": "ct-ahead-application",
                "Description": "Connecticut's AHEAD application"
            },
            {
                "Location": "P:\\HIM-PHI\\52 Fee Schedule\\2025\\AHEAD\\Data\\States\\Rhode Island\\steering committee meeting 2024 07-16_V2.pdf",
                "Name": "steering committee meeting 2024 07-16_V2",
                "Description": "Rhode Island's health care cost trends presentation deck from July 19, 2024"
            }
        ],
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