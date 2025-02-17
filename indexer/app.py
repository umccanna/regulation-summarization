import pdfplumber
from config import get_config
import re
from openai import AzureOpenAI
from azure.cosmos import CosmosClient, ContainerProxy
import getopt
import sys
from pathlib import Path 
import json

def normalize_text(text: str):
    text = re.sub(r'\s+',  ' ', text).strip()
    text = re.sub(r". ,","",text)
    # remove all instances of multiple spaces
    text = text.replace("..",".")
    text = text.replace(". .",".")
    text = text.replace("\n", "")
    text = text.replace("\r", "")

    # replace unicode characters with more usable characters 
    text = text.replace("●", "*")
    text = text.replace("‑", "-")
    text = text.strip()
    
    return text

def strip_emails_and_phone_numbers_and_web_addresses(text):
    text = re.sub(r'(?:[a-zA-Z]|\d|\-|\.)*@cms\.hhs\.gov', "", text).strip()
    text = re.sub(r'\(?\d{3}\)?\-?\d{3}\-\d{4}', "", text).strip()
    text = re.sub(r'(https?|ftp):\/\/([a-zA-Z0-9\-.]+)(\/[^\s]*)?(\?[^\s]*)?', "", text).strip()

    return text

def generate_embeddings(client: AzureOpenAI, text: str):
    return client.embeddings.create(input = [text], model = get_config("EmbeddingsModel")).data[0].embedding

def get_cosmos_container():
    client = CosmosClient(get_config("COSMOS_DB_URL"), get_config("COSMOS_DB_KEY"))
    database = client.get_database_client(get_config("DATABASE_NAME"))
    container = database.get_container_client(get_config("CONTAINER_NAME"))
    return container

def create_document(cosmos_container: ContainerProxy, text: str, embeddings: list[float], chunk_number: int, model_type: str, document_type: str):
    item = {
        "id": f"{document_type}_{chunk_number}",
        "modelType": model_type,
        "text": text,
        "vector": embeddings,
        "documentType": document_type,
        "partitionKey": model_type
    }
    cosmos_container.upsert_item(item)

def upload_fact_sheet(): 
    print('Uploading Fact Sheet')

    cosmos_container = get_cosmos_container()

    openai_client = AzureOpenAI(
        api_key = get_config("AZURE_OPENAI_API_KEY"),
        api_version = "2024-02-01",
        azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
    )

    fact_sheet = get_config("FactSheetLocation")
    
    with pdfplumber.open(fact_sheet) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            page.flush_cache()
            normalized_page_text = normalize_text(page_text)

            embeddings = generate_embeddings(openai_client, normalized_page_text)

            partition_key = get_config("PartitionKey")
            print(f"Saving page {i+1}")
            create_document(cosmos_container, normalized_page_text, embeddings, i, partition_key, "FactSheet")

def delete_document_type(document_type: str):
    print(f'Deleting document {document_type}')
    cosmos_container = get_cosmos_container()
    partition_key = get_config("PartitionKey")
    partition_key = partition_key
    query = f"SELECT * FROM c WHERE c.partitionKey = '{partition_key}' AND c.documentType = '{document_type}'"
    items = cosmos_container.query_items(query=query, enable_cross_partition_query=False)
    deleted_count = 0
    for item in items:
        try:
            cosmos_container.delete_item(item=item['id'], partition_key=partition_key)
            deleted_count += 1
        except Exception as e:
            print(f"Failed to delete item {item['id']}: {str(e)}")

        if deleted_count % 100 == 0:
            print(f'Deleted {deleted_count} items')
    
    print(f'Deleted {deleted_count} items')
            
def upload_final_ruling():
    print('Uploading Final Ruling')

    openai_client = AzureOpenAI(
        api_key = get_config("AZURE_OPENAI_API_KEY"),
        api_version = "2024-02-01",
        azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
    )

    cosmos_container = get_cosmos_container()

    chunk_size = get_config("ChunkSize")
    overlap_size = get_config("Overlap")

    documents = get_config("Documents")

    print(f'Found {len(documents)} to index')

    chunk_accumulator = []
    text_accumulator = []
    total_chunks = 0
    total_chunks_uploaded = 0
    spooling_size = get_config("SpoolingSize")
    chunking_character = get_config("ChunkingCharacter")

    for document in documents:        
        with pdfplumber.open(document["Location"]) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                page.flush_cache()
                # trying to get rid of the pesky extra info
                normalized_page_text = strip_emails_and_phone_numbers_and_web_addresses(page_text)
                normalized_page_text = normalize_text(normalized_page_text)
                for text in normalized_page_text.split(chunking_character):
                    cleaned_up_text = text.strip()
                    # we don't want to index empty strings
                    if len(cleaned_up_text) == 0:
                        continue

                    text_accumulator.append(f'<Chunk><DocumentName>{document["Name"]}</DocumentName><DocumentDescription>{document["Description"]}</DocumentDescription><Page>{i+1}</Page><Text>{cleaned_up_text}</Text></Chunk>')
                    if len(text_accumulator) > chunk_size:
                        chunk_accumulator.append(text_accumulator)
                        total_chunks+=1
                        text_accumulator = []
                    
                    if len(chunk_accumulator) == spooling_size:
                        overlap_and_upload_chunks(cosmos_container, chunk_accumulator, overlap_size, openai_client, True, total_chunks, total_chunks_uploaded, '')
                        total_chunks_uploaded+=(len(chunk_accumulator)-1)
                        chunk_accumulator = chunk_accumulator[(spooling_size-1):]
            
            if len(text_accumulator) != 0:
                chunk_accumulator.append(text_accumulator)
                total_chunks+=1
                text_accumulator = []

            overlap_and_upload_chunks(cosmos_container, chunk_accumulator, overlap_size, openai_client, False, total_chunks, total_chunks_uploaded, '')

def overlap_and_upload_chunks(cosmos_container, chunk_accumulator, overlap_size, openai_client, ignore_last_index, total_chunks, total_already_uploaded, joining_character):
    overlapped_chunks = []
    if len(chunk_accumulator) > 1:
        for i, chunk in enumerate(chunk_accumulator):
            if i == 0:
                if len(chunk_accumulator[i + 1]) < overlap_size:
                    overlapped_chunks.append(chunk + chunk_accumulator[i + 1])
                else:
                    overlapped_chunks.append(chunk + chunk_accumulator[i + 1][:overlap_size])
            elif i == len(chunk_accumulator) - 1:
                if ignore_last_index:
                    continue
                if len(chunk_accumulator[i - 1]) < overlap_size:
                    overlapped_chunks.append(chunk_accumulator[i - 1] + chunk)
                else:
                    overlapped_chunks.append(chunk_accumulator[i - 1][(-1 *overlap_size):] + chunk)
            else:
                new_chunk = None
                if len(chunk_accumulator[i - 1]) < overlap_size:
                    new_chunk = chunk_accumulator[i - 1] + chunk
                else:
                    new_chunk = chunk_accumulator[i - 1][(-1 *overlap_size):] + chunk

                if len(chunk_accumulator[i + 1]) < overlap_size:
                    new_chunk = new_chunk + chunk_accumulator[i + 1]
                else:
                    new_chunk = new_chunk + chunk_accumulator[i + 1][:overlap_size]

                overlapped_chunks.append(new_chunk)

    for i, chunks in enumerate(overlapped_chunks):
        chunked_data = joining_character.join(chunks)

        embeddings = generate_embeddings(openai_client, chunked_data)
        
        partition_key = get_config("PartitionKey")
        print(f"Saving chunk {i+1+total_already_uploaded} of {total_chunks}")
        create_document(cosmos_container, chunked_data, embeddings, i+total_already_uploaded, partition_key, "FinalRuling")

def main():
    try:
        opts, _ = getopt.getopt(sys.argv[1:], "rfdt:", ['upload-final-ruling', 'upload-fact-sheet', 'delete-document-type', 'document-type'])
    except getopt.GetoptError:
        print_help()
        sys.exit(2)
        
    if requesting_help(opts):
        print_help()
        sys.exit(0)        
    
    upload_ruling = get_flag(opts, '-r')
    if upload_ruling:
        upload_final_ruling()

    upload_fact = get_flag(opts, '-f')
    if upload_fact:
        upload_fact_sheet()

    delete_document = get_flag(opts, '-d')
    if delete_document:
        document_type = get_value(opts, '-t')
        delete_document_type(document_type)

def requesting_help(opts):
    help = next((o for o in opts if len(o) > 0 and o[0] == '-h'), None)
    return help != None

def print_help():
    print('You need help...')
    
def get_value(opts, parameter):
    value_arg = next((o for o in opts if len(o) > 0 and o[0] == parameter and len(o) == 2), None)
    return value_arg[1] if value_arg != None else None

def get_flag(opts, parameter):
    value_arg = next((o for o in opts if len(o) > 0 and o[0] == parameter), None)
    return value_arg != None

if __name__ == "__main__":
	sys.exit(main())