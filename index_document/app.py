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

def search_embeddings(embedding: list[float], model_type):
    container = get_cosmos_container()
    items = []
    for item in container.query_items(
        query="SELECT TOP 5 c.id, c.modelType, c.text, c.pageIndex, c.documentType, VectorDistance(c.vector, @embedding) as similiarityScore FROM c ORDER BY VectorDistance(c.vector, @embedding)",
        parameters=[dict(
            name="@embedding", value=embedding
        )],
        partition_key= model_type
    ):
        items.append({
            "id": item["id"],
            "modelType": item["modelType"],
            "text": item["text"],
            "documentType": item["documentType"],
            "similiarityScore": item["similiarityScore"]
        })
    return items

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

            year = get_config("Year")
            model = get_config("Model")
            print(f"Saving page {i+1}")
            create_document(cosmos_container, normalized_page_text, embeddings, i, f"{model}_{year}", "FactSheet")
            
def upload_final_ruling():
    print('Uploading Final Ruling')

    openai_client = AzureOpenAI(
        api_key = get_config("AZURE_OPENAI_API_KEY"),
        api_version = "2024-02-01",
        azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
    )

    cosmos_container = get_cosmos_container()

    rule_location = get_config("FinalRuleLocation")
    chunk_size = get_config("ChunkSize")
    overlap_size = get_config("Overlap")
    chunk_accumulator = []
    text_accumulator = []
    total_chunks = 0
    total_chunks_uploaded = 0
    spooling_size = get_config("SpoolingSize")
    chunking_character = get_config("ChunkingCharacter")
    start_indexing = False

    with pdfplumber.open(rule_location) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            page.flush_cache()
            # trying to get rid of the pesky extra info
            normalized_page_text = strip_emails_and_phone_numbers_and_web_addresses(page_text)
            normalized_page_text = normalize_text(normalized_page_text)

            if not start_indexing and "Summary and Background" in normalized_page_text:
                start_indexing = True

            if not start_indexing:
                print(f'Skipping page {i+1}')
                continue


            text_accumulator.append(f'Page {i+1}')
            for text in normalized_page_text.split(chunking_character):
                text_accumulator.append(text)
                if len(text_accumulator) > chunk_size:
                    chunk_accumulator.append(text_accumulator)
                    total_chunks+=1
                    text_accumulator = []
                
                if len(chunk_accumulator) == spooling_size:
                    overlap_and_upload_chunks(cosmos_container, chunk_accumulator, overlap_size, openai_client, True, total_chunks, total_chunks_uploaded, chunking_character)
                    total_chunks_uploaded+=(len(chunk_accumulator)-1)
                    chunk_accumulator = chunk_accumulator[(spooling_size-1):]
        
        if len(text_accumulator) != 0:
            chunk_accumulator.append(text_accumulator)
            total_chunks+=1
            text_accumulator = []

        overlap_and_upload_chunks(cosmos_container, chunk_accumulator, overlap_size, openai_client, False, total_chunks, total_chunks_uploaded, chunking_character)

def overlap_and_upload_chunks(cosmos_container, chunk_accumulator, overlap_size, openai_client, ignore_last_index, total_chunks, total_already_uploaded, chunking_character):
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
        chunked_data = chunking_character.join(chunks)

        embeddings = generate_embeddings(openai_client, chunked_data)

        year = get_config("Year")
        model = get_config("Model")
        print(f"Saving chunk {i+1+total_already_uploaded} of {total_chunks}")
        create_document(cosmos_container, chunked_data, embeddings, i+total_already_uploaded, f"{model}_{year}", "FinalRuling")

def should_pull_more_embeddings(query: str):

    historical_messages = get_history()
    if len(historical_messages) == 0:
        return True
    
    openai_client = AzureOpenAI(
        api_key = get_config("AZURE_OPENAI_API_KEY"),
        api_version = "2024-02-01",
        azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
    )
    
    messages = []

    messages.append({
        "role": "system",
        "content": "You are a CMS Regulation Analyst that analyzes pricing regulations and provides concise and accurate summaries of the regulations.  Your main job is to assist the user with summarizing and providing interesting insights into the regulations"
    })

    for message in historical_messages:
        messages.append(message)

    messages.append({
                "role": "user",
                "content": f'''
                    Only provide a simple "yes" or "no" in response to this question.  Always respond in all lower case. 

                    I have a vector database full of information regarding CMS regulations.  Based on the below "Prompt", do I need to provide additional context from this database to answer this question?
                    Please be very careful in how you respond and verify that the answer is the correct answer based on the conversaion history.

                    Prompt:
                    {query}
                ''',
            })  

    chat_completion = openai_client.chat.completions.create(
        messages=messages,
        model=get_config("ChatModel")
    )

    decision = chat_completion.choices[0].message.content
    
    print(f'Initial embeddings question response "{decision}"')

    messages.append({
        "role": "assistant",
        "content": decision
    })

    messages.append({
        "role": "user",
        "content": '''Could you double check your previous response and verify that it was correct? If it was correct, echo the exact response.  Otherwise provide the correct response. Only response with a "yes" or "no".

            You Previous Answer: {decision}'''
    })

    chat_completion = openai_client.chat.completions.create(
        messages=messages,
        model=get_config("ChatModel")
    )
    
    decision = chat_completion.choices[0].message.content

    print(f'Checked embeddings question response "{decision}"')

    return decision.lower().strip() == 'yes'

def query_embeddings(query: str):
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
        return []
    
    return results

def get_history():
    conversation_history = []
    cache_path = Path('./conversation_history/convo_cache.json')
    if not cache_path.exists():
        return conversation_history
    
    with open(cache_path, 'r') as convo_reader:
        cached_conversations = json.load(convo_reader)
        for c in cached_conversations:
            conversation_history.append(c)
    
    return conversation_history
        
def add_to_history(new_convo):
    existing_history = get_history()
    for c in new_convo:
        existing_history.append(c)
    cache_path = Path('./conversation_history/convo_cache.json')
    with open(cache_path, 'w') as convo_writer:
        history_json = json.dumps(existing_history)
        convo_writer.write(history_json)

def prompt_open_ai_with_embeddings(embeddings: list[str], query: str):
    openai_client = AzureOpenAI(
        api_key = get_config("AZURE_OPENAI_API_KEY"),
        api_version = "2024-02-01",
        azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
    )

    context = " ".join(embeddings)

    historical_messages = get_history()
    
    messages = []

    messages.append({
        "role": "system",
        "content": "You are a CMS Regulation Analyst that analyzes pricing regulations and provides concise and accurate summaries of the regulations.  Your main job is to assist the user with summarizing and providing interesting insights into the regulations"
    })

    for message in historical_messages:
        messages.append(message)

    new_user_message = {
                "role": "user",
                "content": f'''
                    Only provide responses that can be found in the below "Context:" or from "Context:" in their previous messages based on the user's "Prompt:".  
                    If you are unable to find a response in the below context or previous "Context:" do not make anything up.  Just response with "I'm not sure".

                    Prompt:
                    {query}

                    Context:
                    {context}
                ''',
            }

    messages.append(new_user_message)    

    chat_completion = openai_client.chat.completions.create(
        messages=messages,
        model=get_config("ChatModel")
    )

    print(chat_completion.choices[0].message.content)

    add_to_history([new_user_message, {
        "role": "assistant",
        "content": chat_completion.choices[0].message.content
    }])

def prompt_open_ai(query: str):
    openai_client = AzureOpenAI(
        api_key = get_config("AZURE_OPENAI_API_KEY"),
        api_version = "2024-02-01",
        azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
    )

    historical_messages = get_history()
    
    messages = []

    messages.append({
        "role": "system",
        "content": '''You are a CMS Regulation Analyst that analyzes pricing regulations and provides concise and accurate summaries of the regulations.  
            Your main job is to assist the user with summarizing and providing interesting insights into the regulations'''
    })

    for message in historical_messages:
        messages.append(message)

    new_user_message = {
                "role": "user",
                "content": query,
            }

    messages.append(new_user_message)    

    chat_completion = openai_client.chat.completions.create(
        messages=messages,
        model=get_config("ChatModel")
    )

    print(chat_completion.choices[0].message.content)

    add_to_history([new_user_message, {
        "role": "assistant",
        "content": chat_completion.choices[0].message.content
    }])

def execute_clear_history(): 
    cache_path = Path('./conversation_history/convo_cache.json')
    if cache_path.exists():
        cache_path.unlink()

def main():
    try:
        opts, _ = getopt.getopt(sys.argv[1:], "q:crf", ["query=", "clear-history", 'upload-final-ruling', 'upload-fact-sheet'])
    except getopt.GetoptError:
        print_help()
        sys.exit(2)
        
    if requesting_help(opts):
        print_help()
        sys.exit(0)

    clear_history = get_flag(opts, '-c')
    if clear_history:
        print('Clearing convo history...')
        execute_clear_history()

    query = get_value(opts, '-q')
    if query != None:
        should_get_embeddings = should_pull_more_embeddings(query)
        if should_get_embeddings:
            embeddings = query_embeddings(query)
            if len(embeddings) == 0:
                print('We are unable to complete your request at this time. We were unable to find context for your query.')
                sys.exit(0)
            prompt_open_ai_with_embeddings([e["text"] for e in embeddings], query)
        else:
            prompt_open_ai(query)
        
    
    upload_ruling = get_flag(opts, '-r')
    if upload_ruling:
        upload_final_ruling()

    upload_fact = get_flag(opts, '-f')
    if upload_fact:
        upload_fact_sheet()

    


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