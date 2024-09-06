import pdfplumber
from config import get_config
import re
from openai import AzureOpenAI
from azure.cosmos import CosmosClient

def normalize_text(text: str):
    text = re.sub(r'\s+',  ' ', text).strip()
    text = re.sub(r". ,","",text)
    # remove all instances of multiple spaces
    text = text.replace("..",".")
    text = text.replace(". .",".")
    text = text.replace("\n", "")
    text = text.replace("\r", "")
    text = text.strip()
    
    return text

def generate_embeddings(client: AzureOpenAI, text: str):
    return client.embeddings.create(input = [text], model = get_config("EmbeddingsModel")).data[0].embedding

def get_cosmos_container():
    client = CosmosClient(get_config("COSMOS_DB_URL"), get_config("COSMOS_DB_KEY"))
    database = client.get_database_client(get_config("DATABASE_NAME"))
    container = database.get_container_client(get_config("CONTAINER_NAME"))
    return container

def create_document(text: str, embeddings: list[float], page_index: int, model_type: str, document_type: str):
    container = get_cosmos_container()
    item = {
        "id": f"{document_type}_{page_index}",
        "modelType": model_type,
        "text": text,
        "pageIndex": page_index,
        "vector": embeddings,
        "documentType": document_type,
        "paritionKey": model_type
    }
    container.upsert_item(item)

def search_embeddings(embedding: list[float], model_type):
    container = get_cosmos_container()
    items = []
    for item in container.query_items(
        query="SELECT TOP 3 c.id, c.modelType, c.text, c.pageIndex, c.documentType, VectorDistance(c.vector, @embedding) as similiarityScore FROM c ORDER BY VectorDistance(c.vector, @embedding)",
        parameters=[dict(
            name="@embedding", value=embedding
        )],
        partition_key= model_type
    ):
        items.append({
            "id": item["id"],
            "modelType": item["modelType"],
            "text": item["text"],
            "pageIndex": item["pageIndex"],
            "documentType": item["documentType"],
            "similiarityScore": item["similiarityScore"]
        })
    return items

def upload_fact_sheet(): 
    print('Uploading Fact Sheet')

    openai_client = AzureOpenAI(
        api_key = get_config("AZURE_OPENAI_API_KEY"),
        api_version = "2024-02-01",
        azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
    )

    fact_sheet = get_config("FactSheetLocation")
    with pdfplumber.open(fact_sheet) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            normalized_page_text = normalize_text(page_text)

            embeddings = generate_embeddings(openai_client, normalized_page_text)

            year = get_config("Year")
            model = get_config("Model")
            print(f"Saving page {i+1}")
            create_document(normalized_page_text, embeddings, i, f"{model}_{year}", "FactSheet")

def query_fact_sheet(query: str):
    print('Querying Fact Sheet')

    openai_client = AzureOpenAI(
        api_key = get_config("AZURE_OPENAI_API_KEY"),
        api_version = "2024-02-01",
        azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
    )

    normalized_query = normalize_text(query)

    print(f'Normalized Query: {normalized_query}')

    print('Generating query embeddings')
    embeddings = generate_embeddings(openai_client, normalized_query)

    year = get_config("Year")
    model = get_config("Model")

    print("Searching Embeddings")
    results = search_embeddings(embeddings, f'{model}_{year}')

    if len(results) == 0:
        print('No matches found')
    else:
        for r in results:
            print(f'page: {r["pageIndex"]+1}, similarityScore: {r["similiarityScore"]}, text: {r["text"]}')

#upload_fact_sheet()
query_fact_sheet("What updates were made?")
            