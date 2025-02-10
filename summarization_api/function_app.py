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
from mangers.regulation_manager import RegulationManager

app = func.FunctionApp()

@app.route(route="summarize", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def SummarizationAPI(req: func.HttpRequest) -> func.HttpResponse:
    req_body = req.get_json()

    regulation = req_body["regulation"]
    query = req_body["query"]
    user_id = req_body["userId"]
    conversation_id = req_body["conversationId"] if "conversationId" in req_body else None

    if not regulation:
        return func.HttpResponse(
            "Regulation is required",
            status_code=400
        )
    
    if not query:
        return func.HttpResponse(
            "Query is required",
            status_code=400
        )
    
    if not user_id:
        return func.HttpResponse(
            "User Id is required",
            status_code=400
        )
    
    manager = RegulationManager()

    response_content = manager.query_regulation({
        "regulation": regulation,
        "query": query,
        "conversationId": conversation_id,
        "userId": user_id
    })

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
    
@app.route(route="regulations", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def GetSupportedRegulationsAPI(req: func.HttpRequest) -> func.HttpResponse:
    manager = RegulationManager()
    regulations = manager.get_available_regulations()
    return func.HttpResponse(
        json.dumps(regulations),
        status_code=200,
        mimetype="application/json"
    )

# @app.route(route="regulations", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
# def SetRegulationsAPI(req: func.HttpRequest) -> func.HttpResponse:
#     try:
#         req_body = req.get_json()
#         parition_key = req_body.get('partitionKey')

#         if not parition_key:
#             return func.HttpResponse(
#                 "Request body must contain a partitionKey",
#                 status_code=400
#             )

#         regulations = get_supported_regulations()
#         matching_regulation = None
#         for r in regulations:
#             if r["partitionKey"] == parition_key:
#                 matching_regulation = r
#                 break
        
#         if not matching_regulation:
#             return func.HttpResponse(
#                 "Unsupported selection",
#                 status_code=400
#             )

#         execute_clear_history()

#         cache_path = Path('./conversation_history/selected_regulation.json')
#         with open(cache_path, 'w', encoding='utf-8') as writer:
#             json.dump(matching_regulation, writer)

#         return func.HttpResponse(status_code=200)

#     except Exception as e:
#         logging.error(f"Error setting regulations: {str(e)}")
#         return func.HttpResponse(
#             "Error processing request",
#             status_code=500
#         )

# @app.route(route="regulations/selected", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
# def GetSelectedRegulationAPI(req: func.HttpRequest) -> func.HttpResponse:
#     try:
#         cache_path = Path('./conversation_history/selected_regulation.json')
#         if not cache_path.exists():
#             return func.HttpResponse(
#                 "No regulation selected",
#                 status_code=404
#             )
            
#         with open(cache_path, 'r') as reader:
#             selected_regulation = json.load(reader)
#             return func.HttpResponse(
#                 json.dumps(selected_regulation),
#                 status_code=200,
#                 mimetype="application/json"
#             )
#     except Exception as e:
#         logging.error(f"Error getting selected regulation: {str(e)}")
#         return func.HttpResponse(
#             "Error retrieving selected regulation",
#             status_code=500
#         )

# @app.route(route="clear", auth_level=func.AuthLevel.ANONYMOUS)
# def ClearHistoryAPI(req: func.HttpRequest) -> func.HttpResponse:
#     execute_clear_history()

#     return func.HttpResponse(status_code=200)

# def get_selected_regulation():
#     cache_path = Path('./conversation_history/selected_regulation.json')
#     if not cache_path.exists():
#         logging.info('Selected regulation does not exist')
#         return None
    
#     with open(cache_path, 'r') as reader:
#         return json.load(reader)

# def handle_query(query: str):
#     try:
#         selected_regulation = get_selected_regulation()

#         fact_sheet = None
#         if selected_regulation["hasFACTSheet"]:
#             should_include_fact_sheet = should_pull_fact_sheet(query)
#             if should_include_fact_sheet:
#                 fact_sheet = get_fact_sheet()

#         # Based on CLI's main function logic
#         should_get_embeddings = should_pull_more_embeddings(query)
#         if should_get_embeddings:
#             embeddings = query_embeddings(query)
#             if len(embeddings) == 0:
#                 logging.error("No matches found in vector database. Querying without additional embeddings")
#                 response = prompt_open_ai(fact_sheet, query)
#             else:
#                 response = prompt_open_ai_with_embeddings(fact_sheet, [e["text"] for e in embeddings], query)
#         else:
#             response = prompt_open_ai(fact_sheet, query)

#         return {"result": response}

#     except Exception as e:
#         logging.error(f"Error processing the query: {str(e)}")
#         return None
    
# def normalize_text(text: str):
#     text = re.sub(r'\s+',  ' ', text).strip()
#     text = re.sub(r". ,","",text)
#     text = re.sub(r"\\u(?:[a-z]|\d){4}", "", text)
#     # remove all instances of multiple spaces
#     text = text.replace("..",".")
#     text = text.replace(". .",".")
#     text = text.replace("\n", "")
#     text = text.replace("\r", "")
#     text = text.strip()
    
#     return text

# def generate_embeddings(client: AzureOpenAI, text: str):
#     return client.embeddings.create(input = [text], model = get_config("EmbeddingsModel")).data[0].embedding

# def get_cosmos_container():
#     client = CosmosClient(get_config("COSMOS_DB_URL"), get_config("COSMOS_DB_KEY"))
#     database = client.get_database_client(get_config("DATABASE_NAME"))
#     container = database.get_container_client(get_config("CONTAINER_NAME"))
#     return container

# def get_system_prompt():
#     selected_regulation = get_selected_regulation()
#     if selected_regulation["hasFACTSheet"]:
#         return '''You are a CMS Regulation Analyst that analyzes pricing regulations and provides concise and accurate summaries of the regulations.  
#                 Adhere to these high level guides when responding: 

#                 * You are NOT a counselor or personal care advisor.  DO NOT provide any self help, mental health, or physcial health advice.  Only respond in relation to the regulations you are summarizing. If the regulations you are summarizing involves details related to self-help, counseling, mental health, of physical health then it is premitted to respond in relation to the regulations.  
#                 * When you provide a list or numbered output provide atleast 3 sentences describing each item.  
#                 * When you provide a list do not limit the number of items in the list.  Error on the side of too many items in the list.
#                 * When asked to provide a summary of changes be sure to include any content related to litigations or lawsuits. 
#                 * Your main job is to assist the user with summarizing and providing interesting insights into the regulations.  
#                 * You are also expected to summarize content, when requested, for usage in social media posts.  
#                 * When summarizing content for social media posts it is ok to use emoji's or graphics from outside the context of the conversation history.
#                 * When prompted to do math, double check your work to verify accuracy. 
#                 * When asked to provide page numbers look for the page number tag surrounding the text in the format of <Page {number}>{text}</Page {number}>'''
    
#     return '''You are an Analyst that analyzes documents and provides concise and accurate summaries of the documents.  
#         Adhere to these high level guides when responding: 

#         * You are NOT a counselor or personal care advisor.  DO NOT provide any self help, mental health, or physcial health advice.  Only respond in relation to the document you are summarizing. If the document you are summarizing involves details related to self-help, counseling, mental health, of physical health then it is premitted to respond in relation to the document.  
#         * When you provide a list or numbered output provide atleast 3 sentences describing each item.  
#         * When you provide a list do not limit the number of items in the list.  Error on the side of too many items in the list.
#         * Your main job is to assist the user with summarizing and providing interesting insights into the documents.  
#         * When prompted to do math, double check your work to verify accuracy. 
#         * When asked to provide page numbers look for the page number tag surrounding the text in the format of <Page {number}>{text}</Page {number}>'''

# def search_embeddings(embedding: list[float], model_type):
#     container = get_cosmos_container()
#     items = []
#     for item in container.query_items(
#         query="SELECT TOP 10 c.id, c.modelType, c.text, c.pageIndex, c.documentType, VectorDistance(c.vector, @embedding) as similiarityScore FROM c ORDER BY VectorDistance(c.vector, @embedding)",
#         parameters=[dict(
#             name="@embedding", value=embedding
#         )],
#         partition_key= model_type
#     ):
#         items.append({
#             "id": item["id"],
#             "modelType": item["modelType"],
#             "text": item["text"].encode("utf-8").decode("utf-8"),
#             "documentType": item["documentType"],
#             "similiarityScore": item["similiarityScore"]
#         })

#     logging.info(f'Embedding results found {len(items)}')
#     return items

# def should_pull_fact_sheet(query: str):
#     historical_messages = get_history()
#     if len(historical_messages) == 0:
#         logging.info('No history, pull the fact sheet')
#         return True
    
#     openai_client = AzureOpenAI(
#         api_key = get_config("AZURE_OPENAI_API_KEY"),
#         api_version = "2024-02-01",
#         azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
#     )
    
#     messages = []

#     messages.append({
#         "role": "system",
#         "content": get_system_prompt()
#     })
    
#     for message in historical_messages:
#         messages.append(message)

#     messages.append({
#         "role": "user",
#         "content": f'''
#             Only provide a simple "yes" or "no" in response to this question.  Always respond in all lower case. 

#             I have a high level summary of all the changes that are included in this data. Based on the below "Prompt", is the user asking for a general list of changes?
#             Please be very careful in how you respond and verify that the answer is the correct answer based on the conversaion history.  
#             I would only want to include this summary if it was not included recently in the conversation history and only if the user is specifically asking for a changes.

#             Prompt:
#             {query}
#         ''',
#     })  

#     logging.info('Determining if we should pull the fact sheet')

#     chat_completion = openai_client.chat.completions.create(
#         messages=messages,
#         model=get_config("ChatModel")
#     )

#     decision = chat_completion.choices[0].message.content

#     logging.info(f'Whether or not to include the fact sheet: {decision}')

#     return decision.lower().strip() == 'yes'

# def should_pull_more_embeddings(query: str):
#     historical_messages = get_history()
#     if len(historical_messages) == 0:
#         logging.info('No history, should pull more embeddings')
#         return True
    
#     openai_client = AzureOpenAI(
#         api_key = get_config("AZURE_OPENAI_API_KEY"),
#         api_version = "2024-02-01",
#         azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
#     )
    
#     messages = []

#     messages.append({
#         "role": "system",
#         "content": get_system_prompt()
#     })

#     for message in historical_messages:
#         messages.append(message)

#     logging.info('Determining if we should pull more embeddings')

#     messages.append({
#                 "role": "user",
#                 "content": f'''
#                     Only provide a simple "yes" or "no" in response to this question.  Always respond in all lower case. 

#                     I have a vector database full of information regarding CMS regulations.  Based on the below "Prompt", do I need to provide additional context from this database to answer this question?
#                     Please be very careful in how you respond and verify that the answer is the correct answer based on the conversaion history.

#                     Prompt:
#                     {query}
#                 ''',
#             })  

#     chat_completion = openai_client.chat.completions.create(
#         messages=messages,
#         model=get_config("ChatModel")
#     )

#     decision = chat_completion.choices[0].message.content

#     logging.info(f'Whether or not to pull more embeddings: {decision}')

#     return decision.lower().strip() == 'yes'

# def get_fact_sheet():    
#     selected_regulation = get_selected_regulation()
#     if not selected_regulation:
#         return None
    
#     partition_key = selected_regulation["partitionKey"]
#     has_fact_sheet = selected_regulation["hasFACTSheet"]
#     if not has_fact_sheet:
#         return None

#     container = get_cosmos_container()
#     items = []

#     logging.info('Getting fact sheet')

#     for item in container.query_items(
#         query="SELECT TOP 15 c.id, c.modelType, c.text, c.pageIndex, c.documentType FROM c WHERE c.documentType = 'FactSheet' ORDER BY c.pageIndex ASC",
#         parameters=[],
#         partition_key=partition_key
#     ):
#         items.append({
#             "id": item["id"],
#             "modelType": item["modelType"],
#             "text": item["text"].encode("utf-8").decode("utf-8"),
#             "documentType": item["documentType"]
#         })

#     summarized_fact_sheet = summarize_text(' '.join([e["text"] for e in items]))

#     return summarized_fact_sheet

# def query_embeddings(query: str):
#     openai_client = AzureOpenAI(
#         api_key = get_config("AZURE_OPENAI_API_KEY"),
#         api_version = "2024-02-01",
#         azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
#     )

#     normalized_query = normalize_text(query)
#     logging.info('Normalized Query')

#     logging.info('Generating query embeddings')
#     embeddings = generate_embeddings(openai_client, normalized_query)

#     selected_regulation = get_selected_regulation()
#     if not selected_regulation:
#         return []
    
#     logging.info(f'selected regulation {selected_regulation}')
    
#     partition_key = selected_regulation["partitionKey"]

#     logging.info("Searching Embeddings")
#     results = search_embeddings(embeddings, partition_key)

#     if len(results) == 0:
#         logging.info('No matches found')
#         return []
    
#     return results

# def get_history():
#     conversation_history = []
#     cache_path = Path('./conversation_history/convo_cache.json')
#     if not cache_path.exists():
#         return conversation_history
    
#     with open(cache_path, 'r') as convo_reader:
#         cached_conversations = json.load(convo_reader)
#         for c in cached_conversations:
#             conversation_history.append(c)
    
#     return conversation_history

# def get_supported_regulations():
#     container = get_cosmos_container()
#     supported_regulations = []

#     logging.info('Getting supported regulations')

#     for item in container.query_items(
#         query="SELECT TOP 1 c.regulations FROM c WHERE c.id = 'SupportedRegulations'",
#         parameters=[],
#         partition_key=f'Default'
#     ):
#         for regulation in item["regulations"]:
#             supported_regulations.append({
#                 "partitionKey": regulation["partitionKey"],
#                 "title": regulation["title"],
#                 "hasFACTSheet": regulation["hasFACTSheet"]
#             })

#     return supported_regulations

        
# def add_to_history(new_convo):
#     existing_history = get_history()
#     for c in new_convo:
#         existing_history.append(c)
#     cache_path = Path('./conversation_history/convo_cache.json')
#     with open(cache_path, 'w', encoding='utf-8') as convo_writer:
#         history_json = json.dumps(existing_history)
#         convo_writer.write(history_json)

# def prompt_open_ai_with_embeddings(fact_sheet: str, embeddings: list[str], query: str):
#     openai_client = AzureOpenAI(
#         api_key = get_config("AZURE_OPENAI_API_KEY"),
#         api_version = "2024-02-01",
#         azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
#     )

#     logging.info('Calling OpenAI with embeddings')

#     context = " ".join(embeddings)

#     historical_messages = get_history()

#     messages = []

#     messages.append({
#         "role": "system",
#         "content": get_system_prompt()
#     })

#     for message in historical_messages:
#         messages.append(message)

#     fact_sheet_prompt = ''
#     if fact_sheet:
#         fact_sheet_prompt = f'''
#             Fact Sheet:
#             {fact_sheet}
#         '''

#     new_user_message_content_pre_context = f'''
#         Only provide responses that can be found "Context:" provided below or from the "Context:" in any of the previous messages or any of your previous responses or any previous "Fact Sheet:" based on the user's "Prompt:" .  
#         If you are unable to find a response in the below "Context:" or any previous message "Context:" or any of your previous respsonses or any previous "Fact Sheet:" do not make anything up.  Just response with "I'm not sure how to help you with that.  I may not have been designed to help with your request.".
#         If a "Fact Sheet:" is provided use that content to inform and focus the response. 

#         Prompt:
#         {query}

#     '''

#     new_user_message_content_post_context = fact_sheet_prompt

#     new_user_message = {
#                 "role": "user",
#                 "content": f'''
#                     {new_user_message_content_pre_context}

#                     Context:
#                     {context}

#                     {new_user_message_content_post_context}
#                 ''',
#             }

#     messages.append(new_user_message)

#     chat_completion = openai_client.chat.completions.create(
#         messages=messages,
#         model=get_config("ChatModel")
#     )

#     response_content = chat_completion.choices[0].message.content

#     summarized_context = summarize_text(context)

#     logging.info(f'Summarized context: {summarized_context}')

#     new_user_message["content"] = f'''
#             {new_user_message_content_pre_context}

#             Context:
#             {summarized_context}

#             {new_user_message_content_post_context}
#         '''

#     add_to_history([new_user_message, {
#         "role": "assistant",
#         "content": response_content
#     }])

#     return response_content

# def summarize_text(text: str):
#     openai_client = AzureOpenAI(
#         api_key = get_config("AZURE_OPENAI_API_KEY"),
#         api_version = "2024-02-01",
#         azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
#     )

#     logging.info('Summarizing text')

#     chat_completion = openai_client.chat.completions.create(
#         messages=[
#             {
#                 "role": "system",
#                 "content": "You are a summarizing assistant.  Your goal is to capture the main idea of the content provided."
#             },
#             {
#                 "role": "user",
#                 "content": f'''
#                     Summarize the text provided in the "Text:" below.  Do not provide any additional information that is not related to the text provided. 
#                     Include page numbers from "Text:".  Page numbers are denoted in the format <Page number>text</Page number>.
#                     Pay special attention to any factors, payments, or decimal values and be sure they are included in the summary.

#                     {text}
#                 '''
#             }
#         ],
#         model=get_config("ChatModel")
#     )

#     return chat_completion.choices[0].message.content

# def prompt_open_ai(fact_sheet: str, query: str):
#     openai_client = AzureOpenAI(
#         api_key = get_config("AZURE_OPENAI_API_KEY"),
#         api_version = "2024-02-01",
#         azure_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
#     )

#     logging.info('Calling OpenAI without embeddings')

#     historical_messages = get_history()
    
#     messages = []

#     messages.append({
#         "role": "system",
#         "content": get_system_prompt()
#     })

#     for message in historical_messages:
#         messages.append(message)    

#     fact_sheet_prompt = ''
#     if fact_sheet:
#         fact_sheet_prompt = f'''
#             Fact Sheet:
#             {fact_sheet}
#         '''

#     new_user_message = {
#                 "role": "user",
#                 "content": f'''
#                     Only provide responses that can be found in any previous message "Context:" or any previous message "Fact Sheet:" or any of previous your responses based on the user's "Prompt:".
#                     If you are unable to find a response in any previous message "Context:" or any previous message "Fact Sheet:" or any of your previous responses do not make anything up.  Just response with "I'm not sure how to help you with that.  I may not have been designed to help with your request.".
#                     If a "Fact Sheet:" is provided use that content to inform and focus the response. 

#                     Prompt:
#                     {query}

#                     {fact_sheet_prompt}
#                 ''',
#             }

#     messages.append(new_user_message)    

#     chat_completion = openai_client.chat.completions.create(
#         messages=messages,
#         model=get_config("ChatModel")
#     )

#     add_to_history([new_user_message, {
#         "role": "assistant",
#         "content": chat_completion.choices[0].message.content
#     }])

#     return chat_completion.choices[0].message.content

# def execute_clear_history(): 
#     cache_path = Path('./conversation_history/convo_cache.json')
#     if cache_path.exists():
#         cache_path.unlink()
