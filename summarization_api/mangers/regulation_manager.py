from repositories.regulation_repository import RegulationRepository
from repositories.conversation_repository import ConversationRepository
from services.ai_service import AIService
import logging
import asyncio
import re

class RegulationManager:
    def __init__(self):
        self.__regulation_repository = RegulationRepository()
        self.__conversation_repository = ConversationRepository()
        self.__ai_service = AIService()

    async def __get_matching_regulation(self, regulation_id: str):
        available_regulations = await self.__regulation_repository.get_available_regulations()
        for regulation in available_regulations:
            if regulation["partitionKey"] == regulation_id:
                return regulation
            
        return None
    
    async def migrate_conversations(self, old_user_id, new_user_id):
        return await self.__conversation_repository.migrate_conversations(old_user_id, new_user_id)
    
    async def get_available_regulations(self):
        return await self.__regulation_repository.get_available_regulations()
    
    async def get_conversations(self, user_id):
        return await self.__conversation_repository.get_conversations(user_id)

    def __convert_conversation_history_to_ai_format(self, conversation_log: list, use_raw_prompt: bool):
        converted_history = []

        for log in conversation_log:
            prompt = log["promptRaw"] if use_raw_prompt or "promptImproved" not in log or log["promptImproved"] == "" else log["promptImproved"]

            content_parts = [f'''
                {log["directions"]}

                Prompt: 
                {prompt}
            ''']
            
            if log["contextSummarized"]:
                content_parts.append(
                    f'''
                        Context: 
                        {log["contextSummarized"]}
                    '''
                )

            if log["factSheet"]:
                content_parts.append(
                    f'''
                        Fact Sheet: 
                        {log["factSheet"]}
                    '''
                )

            content_texts = [{
                    "type": "text",
                    "text": c.strip()
                } for c in ''.join(content_parts).split("\n")]
            
            content_parts_with_newlines = []
            for i, text in enumerate(content_texts):
                content_parts_with_newlines.append(text)
                if i != len(content_texts) - 1:
                    content_parts_with_newlines.append({
                        "type": "text",
                        "text": "\n"
                    })
            
            converted_history.append({
                "role": "user",
                "content": content_parts_with_newlines
            })

            if log["response"]:
                converted_history.append({
                    "role": "assistant",
                    "content": [{ 
                        "type": "text",
                        "text": log["response"]
                    }]
                })
        
        return converted_history
    
    def __get_directions_with_context(self):
        return '''
            Use the "Context:" provided below, any previous message "Context:", your previous responses, or any previous "Fact Sheet:" to respond to the user's "Prompt:".

            - If the answer is explicitly stated in the "Context:", prioritize that information.  
            - If the answer is not directly stated but can be **reasonably inferred** using logical deduction from the provided "Context:" or "Fact Sheet:", do so.  
                - **When making such inferences, explain the reasoning step-by-step, clearly referencing the parts of the Context or Fact Sheet used to make the inference.**  
            - If you cannot infer a reasonable answer from the provided information, respond with: "I'm not sure how to help you with that. I may not have been designed to help with your request."

            When responding, ensure that all reasoning is grounded in the provided "Context:", previous "Fact Sheet:", or prior responses. Do **not** make up information beyond what can be logically inferred.

        '''
    
    def __get_directions_without_context(self):
        return '''
            Only provide responses based on any previous message "Context:", any previous "Fact Sheet:", or any of your previous responses when answering the user's "Prompt:".  

            - If the answer is explicitly stated in any previous "Context:", "Fact Sheet:", or prior responses, use that information verbatim or summarize it accurately.  
            - If the answer is not explicitly stated but can be **reasonably inferred** from existing "Context," "Fact Sheet," or previous responses, provide a response **only if it aligns logically with known information**.  
            - If no relevant information exists, respond with:  
            **"I'm not sure how to help you with that. The available information does not contain an answer to your request."**  

            **Inference Rules:**  
            - You may **reword or synthesize** known facts, but do not introduce **new** details or assumptions.  
            - If prior responses imply a partial answer, clarify what is known while noting any missing details.  

            If a "Fact Sheet:" is provided, prioritize its content to inform and focus the response.

        '''

    def __merge_embeddings(self, embeddings):
        try:
            if len(embeddings) > 0 and "<Chunk>" in embeddings[0] and "<DocumentName>" in embeddings[0] and "<Text>" in embeddings[0] and "<Page>" in embeddings[0]:
                merged = []
                merged_tracker = set()
                for e in embeddings:
                    for chunk in e.split("</Chunk><Chunk>"):
                        document_name_pieces = chunk.split("<DocumentName>")
                        if len(document_name_pieces) < 2:
                            return embeddings
                        
                        text_pieces = chunk.split("<Text>")
                        if len(text_pieces) < 2:
                            return embeddings
                        
                        page_pieces = chunk.split("<Page>")
                        if len(page_pieces) < 2:
                            return embeddings

                        document_name = document_name_pieces[1][:document_name_pieces[1].find("</DocumentName>")]
                        document_text = text_pieces[1][:text_pieces[1].find("</Text>")]
                        document_page = page_pieces[1][:page_pieces[1].find("</Text>")]

                        key = f"{document_name}_{document_text}_{document_page}"
                        if key not in merged_tracker:
                            merged_tracker.add(key)
                            if not chunk.startswith("<Chunk>"):
                                chunk = "<Chunk>" + chunk
                            if not chunk.endswith("</Chunk>"):
                                chunk = chunk + "</Chunk>"
                            merged.append(chunk)
                return merged
        except:
            logging.exception("Failed to merge embeddings. Defaulting to unmerged embeddings")
                    
        return embeddings

    def __group_embeddings_by_document_name(self, embeddings):
        grouped_embeddings = []

        if len(embeddings) > 0 and "<DocumentName>" in embeddings[0]["text"]:
            for e in embeddings:
                match = re.search(r"<DocumentName>(.*?)</DocumentName>", e["text"])
                print("Match", match)
                document_name = match.group(1) if match else None

                if not document_name:
                    document_name = "Default"

                matching_group = next((g for g in grouped_embeddings if g["name"] == document_name), None)
                if matching_group:
                    matching_group["text"].append(e["text"])
                else:
                    grouped = {
                        "name": document_name,
                        "text": [e["text"]]
                    }
                    grouped_embeddings.append(grouped)
        else:
            grouped = {
                "name": "Default",
                "text": []
            }
            for e in embeddings:
                grouped["text"].append(e["text"])
            grouped_embeddings.append(grouped)
            
        return grouped_embeddings
    
    def __merge_grouped_embeddings(self, grouped_embeddings):
        for g in grouped_embeddings:
            merged_embeddings = self.__merge_embeddings(g["text"])
            g["text"] = merged_embeddings

    async def query_regulation(self, request):
        try:
            selected_regulation = await self.__get_matching_regulation(request["regulation"])

            conversation = await self.__conversation_repository.get_conversation(request["userId"], request["conversationId"]) if request["conversationId"] else None
            if not conversation:
                summarized_query = await self.__ai_service.generate_title(request["query"], 30)
                conversation = await self.__conversation_repository.create_conversation(request["userId"], summarized_query, request["regulation"])

            # Limit messages sent to OpenAI (e.g., last 5)
            CONTEXT_LIMIT = 7
            limited_conversation_log = conversation["log"][-CONTEXT_LIMIT:] if len(conversation["log"]) > CONTEXT_LIMIT else conversation["log"]


            ai_formatted_conversation_history = self.__convert_conversation_history_to_ai_format(limited_conversation_log, False)
            already_has_fact_sheet = False
            for log in conversation["log"]:
                if log["factSheet"]:
                    already_has_fact_sheet = True
                    break
            
            
            if already_has_fact_sheet:
                logging.info("Fact sheet already in conversation")
            else:
                logging.info("No fact sheet found in conversation history")

            fact_sheet = None
            if selected_regulation["hasFACTSheet"] and not already_has_fact_sheet:
                should_include_fact_sheet = await self.__ai_service.should_pull_fact_sheet(request["query"], ai_formatted_conversation_history, selected_regulation)
                if should_include_fact_sheet:
                    fact_sheet = await self.__regulation_repository.get_fact_sheet(selected_regulation)
                    fact_sheet = await self.__ai_service.summarize_text(fact_sheet)

            directions = None
            response = None
            context_raw = None
            context_summarized = None
            user_query = request["query"]
            improved_user_query = user_query
            if len(ai_formatted_conversation_history) > 0:
                improved_user_query = await self.__ai_service.improve_query(user_query, ai_formatted_conversation_history)    
                logging.info(f'Improved Query: {improved_user_query}')
            else: 
                logging.info('Not improving query.  Not enough context to be of any assistance')
                
            generate_query_embeddings = await self.__ai_service.generate_embeddings(improved_user_query)

            embeddings = await self.__regulation_repository.query_embeddings(generate_query_embeddings, selected_regulation)
            if len(embeddings) == 0:
                logging.error("No matches found in vector database. Querying without additional embeddings")
                directions = self.__get_directions_without_context()
                response = await self.__ai_service.call_without_context(
                    ai_formatted_conversation_history,
                    selected_regulation,
                    directions,
                    fact_sheet,
                    improved_user_query
                )
            else:
                directions = self.__get_directions_with_context()
                
                grouped_embeddings = self.__group_embeddings_by_document_name(embeddings)
                
                # since we overlap embeddings while indexing we have to unoverlap them during search to cut down on context size
                # this can cut the context by %25 in some cases
                self.__merge_grouped_embeddings(grouped_embeddings)

                sem = asyncio.Semaphore(2)

                async def summarize_text_with_sem(context):
                    async with sem:
                        return await self.__ai_service.summarize_text(context)
                    
                def combine_and_clean_embeddings(embedding_text):
                    return " ".join(embedding_text).replace("> <", "><")
                    
                merged_context_raw = self.__merge_embeddings([e["text"] for e in embeddings])
                context_raw = combine_and_clean_embeddings(merged_context_raw)

                results = await asyncio.gather(
                    self.__ai_service.call_with_context(
                        context_raw, 
                        ai_formatted_conversation_history, 
                        selected_regulation,
                        directions,
                        fact_sheet,
                        improved_user_query
                    ),
                    *[summarize_text_with_sem(combine_and_clean_embeddings(t["text"])) for t in grouped_embeddings]
                )
                
                response = results[0]
                context_summarized = "\n\n".join(results[1:])

            logging.info("Saving conversation log")
            await self.__conversation_repository.save_conversation_log({
                "conversationId": conversation["id"],
                "userId": request["userId"],
                "promptRaw": user_query,
                "promptImproved": improved_user_query,
                "contextRaw": context_raw,
                "contextSummarized": context_summarized,
                "factSheet": fact_sheet,
                "directions": directions,
                "response": response
            })
            
            logging.info("Finished saving conversation log")

            return {
                "result": response,
                "conversationId": conversation["id"]
            }

        except:
            logging.exception("Error processing the query")
            return None