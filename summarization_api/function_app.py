import azure.functions as func
import datetime
import logging
from config import get_config
import re
from openai import AzureOpenAI
from azure.cosmos import CosmosClient, ContainerProxy
import getopt
import sys
from pathlib import Path 
import json

app = func.FunctionApp()

@app.route(route="summarize", auth_level=func.AuthLevel.ANONYMOUS)
def SummarizationAPI(req: func.HttpRequest) -> func.HttpResponse:
    
    query = req.params.get('query')

    if not query:
        return func.HttpResponse(
            "Please pass a query parameter either in the query string or request body.",
            status_code=400
        )

    # Integrate the CLI logic
    response_content = handle_query(query)

    if response_content:
        return func.HttpResponse(
            json.dumps(response_content),
            status_code=200,
            mimetype="application/json"
        )
    else:
        return func.HttpResponse(
            "We are unable to complete your request at this time.",
            status_code=500
        )
    
@app.route(route="clear", auth_level=func.AuthLevel.ANONYMOUS)
def ClearHistoryAPI(req: func.HttpRequest) -> func.HttpResponse:
    execute_clear_history()

    return func.HttpResponse(status_code=200)

def handle_query(query: str):
    try:
        should_include_fact_sheet = should_pull_fact_sheet(query)
        fact_sheet = []
        if should_include_fact_sheet:
            fact_sheet = get_fact_sheet()

        # Based on CLI's main function logic
        should_get_embeddings = should_pull_more_embeddings(query)
        if should_get_embeddings:
            embeddings = query_embeddings(query)
            if len(embeddings) == 0:
                logging.error("No matches found in vector database.")
                return None
            response = prompt_open_ai_with_embeddings([e["text"] for e in fact_sheet], [e["text"] for e in embeddings], query)
        else:
            response = prompt_open_ai([e["text"] for e in fact_sheet], query)

        return {"result": response}

    except Exception as e:
        print(e)
        logging.error(f"Error processing the query: {str(e)}")
        return None
    
def normalize_text(text: str):
    text = re.sub(r'\s+',  ' ', text).strip()
    text = re.sub(r". ,","",text)
    text = re.sub(r"\\u(?:[a-z]|\d){4}", "", text)
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

def get_system_prompt():
    return '''You are a CMS Regulation Analyst that analyzes pricing regulations and provides concise and accurate summaries of the regulations.  
            Adhere to these high level guides when responding: 

            * You are NOT a counselor or personal care advisor.  DO NOT provide any self help, mental health, or physcial health advice.  Only respond in relation to the regulations you are summarizing. If the regulations you are summarizing involves details related to self-help, counseling, mental health, of physical health then it is premitted to respond in relation to the regulations.  
            * When you provide a list or numbered output provide atleast 3 sentences describing each item.  
            * When you provide a list do not limit the number of items in the list.  Error on the side of too many items in the list.
            * When asked to provide a summary of changes be sure to include any content related to litigations or lawsuits. 
            * Your main job is to assist the user with summarizing and providing interesting insights into the regulations.  
            * You are also expected to summarize content, when requested, for usage in social media posts.  
            * When summarizing content for social media posts it is ok to use emoji's or graphics from outside the context of the conversation history.
            * When prompted to do math, double check your work to verify accuracy. 
            * When asked to provide page numbers look for the page number tag surrounding the text in the format of <Page {number}>{text}</Page {number}>'''


def search_embeddings(embedding: list[float], model_type):
    container = get_cosmos_container()
    items = []
    for item in container.query_items(
        query="SELECT TOP 10 c.id, c.modelType, c.text, c.pageIndex, c.documentType, VectorDistance(c.vector, @embedding) as similiarityScore FROM c ORDER BY VectorDistance(c.vector, @embedding)",
        parameters=[dict(
            name="@embedding", value=embedding
        )],
        partition_key= model_type
    ):
        items.append({
            "id": item["id"],
            "modelType": item["modelType"],
            "text": item["text"].encode("utf-8").decode("utf-8"),
            "documentType": item["documentType"],
            "similiarityScore": item["similiarityScore"]
        })

    print(f'Embedding results found {len(items)}')
    return items

def should_pull_fact_sheet(query: str):
    historical_messages = get_history()
    if len(historical_messages) == 0:
        print('No history, pull the fact sheet')
        return True
    
    openai_client = AzureOpenAI(
        api_key = get_config("AZURE_OPENAI_API_KEY"),
        api_version = "2024-02-01",
        azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
    )
    
    messages = []

    messages.append({
        "role": "system",
        "content": get_system_prompt()
    })
    
    for message in historical_messages:
        messages.append(message)

    messages.append({
        "role": "user",
        "content": f'''
            Only provide a simple "yes" or "no" in response to this question.  Always respond in all lower case. 

            I have a high level summary of all the changes that are included in this data. Based on the below "Prompt", is the user asking for a general list of changes?
            Please be very careful in how you respond and verify that the answer is the correct answer based on the conversaion history.  
            I would only want to include this summary if it was not included recently in the conversation history and only if the user is specifically asking for a changes.

            Prompt:
            {query}
        ''',
    })  

    chat_completion = openai_client.chat.completions.create(
        messages=messages,
        model=get_config("ChatModel")
    )

    decision = chat_completion.choices[0].message.content

    print(f'Whether or not to include the fact sheet: {decision}')

    return decision.lower().strip() == 'yes'

def should_pull_more_embeddings(query: str):
    historical_messages = get_history()
    if len(historical_messages) == 0:
        print('No history, should pull more embeddings')
        return True
    
    openai_client = AzureOpenAI(
        api_key = get_config("AZURE_OPENAI_API_KEY"),
        api_version = "2024-02-01",
        azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
    )
    
    messages = []

    messages.append({
        "role": "system",
        "content": get_system_prompt()
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

    print(f'Whether or not to pull more embeddings: {decision}')

    return decision.lower().strip() == 'yes'

def get_fact_sheet():    
    year = get_config("Year")
    model = get_config("Model")
    container = get_cosmos_container()
    items = []
    for item in container.query_items(
        query="SELECT TOP 15 c.id, c.modelType, c.text, c.pageIndex, c.documentType FROM c WHERE c.documentType = 'FactSheet' ORDER BY c.pageIndex ASC",
        parameters=[],
        partition_key=f'{model}_{year}'
    ):
        items.append({
            "id": item["id"],
            "modelType": item["modelType"],
            "text": item["text"].encode("utf-8").decode("utf-8"),
            "documentType": item["documentType"]
        })

    print(f'found fact sheet items {items}')
    return items

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
    with open(cache_path, 'w', encoding='utf-8') as convo_writer:
        history_json = json.dumps(existing_history)
        convo_writer.write(history_json)

def prompt_open_ai_with_embeddings(fact_sheet_parts: list[str], embeddings: list[str], query: str):
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
        "content": get_system_prompt()
    })

    for message in historical_messages:
        messages.append(message)

    fact_sheet = " ".join(fact_sheet_parts)

    fact_sheet_prompt = ''
    if len(fact_sheet_parts) > 0:
        fact_sheet_prompt = f'''
            Fact Sheet:
            {fact_sheet}
        '''
    new_user_message = {
                "role": "user",
                "content": f'''
                    Only provide responses that can be found "Context:" provided below or from the "Context:" in previous messages based on the user's "Prompt:".  
                    If you are unable to find a response in the below "Context:" or previous "Context:" do not make anything up.  Just response with "I'm not sure".
                    If a "Fact Sheet:" is provided use that content to inform and focus the response. 

                    Prompt:
                    {query}

                    Context:
                    {context}

                    {fact_sheet_prompt}
                ''',
            }

    messages.append(new_user_message)    

    print(f'Messages to be sent. {messages}')

    chat_completion = openai_client.chat.completions.create(
        messages=messages,
        model=get_config("ChatModel")
    )

    print(f'Result from open AI: {chat_completion}')

    add_to_history([new_user_message, {
        "role": "assistant",
        "content": chat_completion.choices[0].message.content
    }])

    return chat_completion.choices[0].message.content

def prompt_open_ai(fact_sheet_parts: list[str], query: str):
    openai_client = AzureOpenAI(
        api_key = get_config("AZURE_OPENAI_API_KEY"),
        api_version = "2024-02-01",
        azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
    )

    historical_messages = get_history()
    
    messages = []

    messages.append({
        "role": "system",
        "content": get_system_prompt()
    })

    for message in historical_messages:
        messages.append(message)    

    fact_sheet = " ".join(fact_sheet_parts)
    fact_sheet_prompt = ''
    if len(fact_sheet_parts) > 0:
        fact_sheet_prompt = f'''
            Fact Sheet:
            {fact_sheet}
        '''

    new_user_message = {
                "role": "user",
                "content": f'''
                    Only provide responses that can be found in the "Context:" of previous messages based on the user's "Prompt:".  
                    If you are unable to find a response in the below "Context:" or previous "Context:" do not make anything up.  Just response with "I'm not sure".
                    If a "Fact Sheet:" is provided use that content to inform and focus the response. 

                    Prompt:
                    {query}

                    {fact_sheet_prompt}
                ''',
            }

    messages.append(new_user_message)    

    chat_completion = openai_client.chat.completions.create(
        messages=messages,
        model=get_config("ChatModel")
    )

    #print(chat_completion.choices[0].message.content)

    add_to_history([new_user_message, {
        "role": "assistant",
        "content": chat_completion.choices[0].message.content
    }])

    return chat_completion.choices[0].message.content

def execute_clear_history(): 
    cache_path = Path('./conversation_history/convo_cache.json')
    if cache_path.exists():
        cache_path.unlink()
