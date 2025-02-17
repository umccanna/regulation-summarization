import logging
from config import get_config
from openai import AzureOpenAI
import re

class AIService:
    def __init__(self):
        self.__api_key = get_config("AZURE_OPENAI_API_KEY")
        self.__api_endpoint = get_config("AZURE_OPENAI_ENDPOINT")
        self.__api_version = "2024-02-01"
        self.__chat_model = get_config("ChatModel")
    
    def __get_client(self):
        return AzureOpenAI(
            api_key = self.__api_key,
            api_version = self.__api_version,
            azure_endpoint = self.__api_endpoint
        )

    def __get_system_prompt(self, regulation):
        if regulation["partitionKey"] in ["OPPS_2024", "OPPS_2025", "PROF_2025"]:
            return '''
                You are a CMS Regulation Analyst that analyzes pricing regulations and provides concise and accurate summaries of the regulations.  
                    Adhere to these high level guides when responding: 

                    * You are NOT a counselor or personal care advisor.  DO NOT provide any self help, mental health, or physcial health advice.  Only respond in relation to the regulations you are summarizing. If the regulations you are summarizing involves details related to self-help, counseling, mental health, of physical health then it is premitted to respond in relation to the regulations.  
                    * When you provide a list or numbered output provide atleast 3 sentences describing each item.  
                    * When you provide a list do not limit the number of items in the list.  Error on the side of too many items in the list.
                    * When asked to provide a summary of changes be sure to include any content related to litigations or lawsuits. 
                    * Your main job is to assist the user with summarizing and providing interesting insights into the regulations.  
                    * You are also expected to summarize content, when requested, for usage in social media posts.  
                    * When summarizing content for social media posts it is ok to use emoji's or graphics from outside the context of the conversation history.
                    * When prompted to do math, double check your work to verify accuracy. 
                    * When asked to provide page numbers look for the page number tag surrounding the text in the format of <Page {number}>{text}</Page {number}>
            '''
        
        if regulation["partitionKey"] in ["AHEAD_NOFO_2023", "AHEAD_2ND_ROUND_NARRATIVE_2024"]:        
            return '''
                You are an Analyst that analyzes documents and provides concise and accurate summaries of the documents.  
                Adhere to these high level guides when responding: 

                * You are NOT a counselor or personal care advisor.  DO NOT provide any self help, mental health, or physcial health advice.  Only respond in relation to the document you are summarizing. If the document you are summarizing involves details related to self-help, counseling, mental health, of physical health then it is premitted to respond in relation to the document.  
                * When you provide a list or numbered output provide atleast 3 sentences describing each item.  
                * When you provide a list do not limit the number of items in the list.  Error on the side of too many items in the list.
                * Your main job is to assist the user with summarizing and providing interesting insights into the documents.  
                * When prompted to do math, double check your work to verify accuracy. 
                * When asked to provide page numbers look for the page number tag surrounding the text in the format of <Page {number}>{text}</Page {number}>
            '''
        
        if regulation["partitionKey"] in ["AHEAD_NOFO_ALL_STATE_NARRATIVES", "AHEAD_NOFO_HAWAII_NARRATIVE", "AHEAD_NOFO_VERMONT_NARRATIVE", "AHEAD_NOFO_CONNECTICUT_NARRATIVE", "AHEAD_NOFO_MARYLAND_NARRATIVE", "AHEAD_NOFO_NEW_YORK_NARRATIVE", "AHEAD_NOFO_RHODE_ISLAND_NARRATIVE"]:
            return '''
                You are an Analyst that analyzes documents and provides concise and accurate summaries of the documents. 
                Adhere to these high level guides when responding: 

                * You are NOT a counselor or personal care advisor.  DO NOT provide any self help, mental health, or physcial health advice.  Only respond in relation to the document you are summarizing. If the document you are summarizing involves details related to self-help, counseling, mental health, of physical health then it is premitted to respond in relation to the document.  
                * When you provide a list or numbered output provide atleast 3 sentences describing each item.  
                * When you provide a list do not limit the number of items in the list.  Error on the side of too many items in the list.
                * Your main job is to assist the user with summarizing and providing interesting insights into the documents.  
                * When prompted to do math, double check your work to verify accuracy. 
                * If referencing content, **include the document name and page number when applicable.**  Each retrieved documnet chunk contains the following metadata"
                    - **`<DocumentName>`** - The name of the document.  
                    - **`<DocumentDescription>`** - A short description of the document.  
                    - **`<Page>`** - The page number associated with the chunk.  
                    - **`<Text>`** - The actual content of the chunk.  
            '''
        
        return None

    def should_pull_fact_sheet(self, query: str, conversation_history: list, regulation):
        if len(conversation_history) == 0:
            logging.info('No history, pull the fact sheet')
            return True
        
        openai_client = self.__get_client()
        
        messages = []

        system_prompt = self.__get_system_prompt(regulation)
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        else:
            logging.warning(f'No system prompt found for {regulation}')
        
        for message in conversation_history:
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

        logging.info('Determining if we should pull the fact sheet')

        chat_completion = openai_client.chat.completions.create(
            messages=messages,
            model=self.__chat_model
        )

        decision = chat_completion.choices[0].message.content

        logging.info(f'Whether or not to include the fact sheet: {decision}')

        return decision.lower().strip() == 'yes'
    
    def summarize_text(self, text: str, summary_max_length: int=None):
        openai_client = self.__get_client()

        logging.info('Summarizing text')

        if summary_max_length is not None:
            text = f'''
                Max Length: {summary_max_length}

                {text}
            '''

        chat_completion = openai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a summarizing assistant.  Your goal is to capture the main idea of the content provided."
                },
                {
                    "role": "user",
                    "content": f'''
                        Summarize the text provided in the 'Text:' below. If the text is suitable as a title, provide a concise and compelling title. 
                        Otherwise, generate a general summary. Do not include any labels or prefixes in the response. If a 'Max Length:' is provided, 
                        strictly limit the summary to that length, even if it means omitting page numbers or key numerical details. 
                        Ensure any referenced page numbers, document names, or document descriptions and important numerical values (such as factors, payments, or decimal values) 
                        are included unless constrained by the max length.

                        Text:
                        {text}
                    '''
                }
            ],
            model=get_config("ChatModel")
        )

        return chat_completion.choices[0].message.content
    
    def __normalize_text(self, text: str):
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
    
    def generate_embeddings(self, text: str):
        openai_client = self.__get_client()
        normalized_query = self.__normalize_text(text)
        return openai_client.embeddings.create(input = [normalized_query], model = get_config("EmbeddingsModel")).data[0].embedding
    
    def should_pull_more_embeddings(self, query: str, conversation_history: list, regulation):
        if len(conversation_history) == 0:
            logging.info('No history, should pull more embeddings')
            return True
        
        openai_client = self.__get_client()
        
        messages = []

        system_prompt = self.__get_system_prompt(regulation)
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        else:
            logging.warning(f'No system prompt found for {regulation}')

        for message in conversation_history:
            messages.append(message)

        logging.info('Determining if we should pull more embeddings')

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
            model=self.__chat_model
        )

        decision = chat_completion.choices[0].message.content

        logging.info(f'Whether or not to pull more embeddings: {decision}')

        return decision.lower().strip() == 'yes'
    
    def improve_query(self, query: str, conversation_history: list):
        openai_client = self.__get_client()

        messages = []

        messages.append({
            "role": "system",
            "content": '''
                Your task is to rewrite and improve user queries by incorporating relevant context from previous messages, responses, and fact sheets. The goal is to refine the query for better clarity, specificity, and completeness while preserving the user's original intent.

                ### **Rules for Query Enhancement:**
                1. **Context-Aware Rewriting**  
                - Identify and integrate any relevant information from past messages, responses, or fact sheets.
                - If multiple relevant contexts exist, combine them naturally while maintaining coherence.
                - Pay special attention to references to previous numbered lists in responses. 

                2. **Preserve the User's Intent**  
                - Do not alter the fundamental meaning or introduce assumptions beyond what is explicitly available.

                3. **Improve Clarity & Precision**  
                - Make the query clearer and more informative without unnecessary verbosity.
                - Resolve vague or ambiguous wording where possible.

                4. **Avoid Redundancy or Overloading**  
                - Do not include excessive details that do not add value.
                - Ensure the rewritten query remains concise and natural.

                5. **Edge Case Handling**  
                - If no relevant context is found, return the original query unchanged.

                ### **Output Format:**  
                - Return only the rewritten and improved query, with no additional explanations or commentary.
                - If no relevant context exists, return the original user query as-is.

                Failure to follow these rules will result in incorrect behavior.
            '''
        })
        
        for message in conversation_history:
            messages.append(message)

        messages.append({
            "role": "user",
            "content": f'''
                Analyze the "Prompt:" and improve it by incorporating relevant context from previous messages, responses, or fact sheets.  

                ### **Guidelines for Query Improvement:**
                - **Enhance Clarity & Completeness** - Ensure the rewritten query is more precise and informative.
                - **Naturally Integrate Relevant Context** - If past context helps refine the query, seamlessly incorporate it.
                - **Preserve the User's Intent** - Do not change the meaning of the original query.
                - **Avoid Redundant or Unnecessary Details** - Only include what strengthens the query.
                - **Maintain a Natural Tone** - Ensure the rewritten query feels human-like and intuitive.

                If no relevant context is found, return the original "Prompt:" unchanged.

                ---

                Prompt:  
                {query}
            '''
        })
        
        chat_completion = openai_client.chat.completions.create(
            messages=messages,
            model=get_config("ChatModel")
        )

        response_content = chat_completion.choices[0].message.content

        return response_content

    
    def call_with_context(self, context: str, conversation_history: list, regulation, directions: str, fact_sheet: str, query: str):
        openai_client = self.__get_client()

        messages = []

        system_prompt = self.__get_system_prompt(regulation)
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        else:
            logging.warning(f'No system prompt found for {regulation}')

        for message in conversation_history:
            messages.append(message)

        fact_sheet_prompt = ''
        if fact_sheet:
            fact_sheet_prompt = f'''
                Fact Sheet:
                {fact_sheet}
            '''

        new_user_message_content_pre_context = f'''
            {directions}

            Prompt:
            {query}

        '''

        new_user_message_content_post_context = fact_sheet_prompt

        new_user_message = {
                    "role": "user",
                    "content": f'''
                        {new_user_message_content_pre_context}

                        Context:
                        {context}

                        {new_user_message_content_post_context}
                    ''',
                }

        messages.append(new_user_message)

        chat_completion = openai_client.chat.completions.create(
            messages=messages,
            model=get_config("ChatModel")
        )

        response_content = chat_completion.choices[0].message.content

        return response_content
    

    def call_without_context(self, conversation_history: list, regulation, directions: str, fact_sheet: str, query: str):
        openai_client = self.__get_client()

        logging.info('Calling OpenAI without embeddings')
        
        messages = []

        system_prompt = self.__get_system_prompt(regulation)
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        else:
            logging.warning(f'No system prompt found for {regulation}')

        for message in conversation_history:
            messages.append(message)    

        fact_sheet_prompt = ''
        if fact_sheet:
            fact_sheet_prompt = f'''
                Fact Sheet:
                {fact_sheet}
            '''

        new_user_message = {
                    "role": "user",
                    "content": f'''
                        {directions}

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

        return chat_completion.choices[0].message.content