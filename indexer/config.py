import os
from dotenv import load_dotenv

# Load the environment variables from .env file
load_dotenv()

__configuration = {
    "Default": {
        "Documents":[
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_ACOs_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_ACOs_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_ACOs_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_ambulance_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_ambulance_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_ambulance_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_ASC_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_ASC_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_ASC_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_CAH_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_CAH_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_CAH_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_clinical_lab_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_clinical_lab_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_clinical_lab_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_dialysis_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_dialysis_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_dialysis_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_DME_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_DME_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_DME_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_FQHC_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_FQHC_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_FQHC_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_HHA_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_HHA_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_HHA_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_hospice_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_hospice_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_hospice_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_hospital_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_hospital_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_hospital_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_IRF_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_IRF_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_IRF_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_LTCH_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_LTCH_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_LTCH_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_MA_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_MA_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_MA_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_OPD_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_OPD_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_OPD_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_PartB_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_PartB_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_PartB_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_PartD_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_PartD_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_PartD_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_Physician_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_Physician_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_Physician_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_psych_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_psych_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_psych_FINAL_SEC"
            },
            {
                "Location": "T:\\Data\\CMS\\Fee Schedules\\MedPac\\23 Payment Basics\\MedPAC_Payment_Basics_23_SNF_FINAL_SEC.pdf",
                "Name": "MedPAC_Payment_Basics_23_SNF_FINAL_SEC",
                "Description": "MedPAC_Payment_Basics_23_SNF_FINAL_SEC"
            }
        ],
        "FactSheetLocation": None,
        "ConvertToImagesFirst": True,
        "TempImageLocation": "C:\\src\\data\\extracted_images",
        "CleanupTempData": False,
        "StartingChunkCount": 0,
        "UseAIChunking": True,
        "PartitionKey": "MEDPAC_PAYMENT_BASICS_23",
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