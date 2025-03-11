from repositories.regulation_repository import RegulationRepository
from services.ai_service import AIService
import logging

class RegulationManager:
    def __init__(self):
        self.__regulation_repository = RegulationRepository()
        self.__ai_service = AIService()

    def __get_matching_regulation(self, regulation_id: str):
        available_regulations = self.__regulation_repository.get_available_regulations()
        for regulation in available_regulations:
            if regulation["partitionKey"] == regulation_id:
                return regulation
            
        return None
    
    def migrate_conversations(self, old_user_id, new_user_id):
        return self.__regulation_repository.migrate_conversations(old_user_id, new_user_id)
    
    def get_available_regulations(self):
        return self.__regulation_repository.get_available_regulations()
    
    def get_conversations(self, user_id):
        return self.__regulation_repository.get_conversations(user_id)

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

            
            converted_history.append({
                "role": "user",
                "content": ''.join(content_parts)
            })

            if log["response"]:
                converted_history.append({
                    "role": "assistant",
                    "content": log["response"]
                })
        
        return converted_history
    
    def __get_directions_with_context(self):
        return '''
            Use the "Context:" provided below, any previous message "Context:", your previous responses, or any previous "Fact Sheet:" to respond to the user's "Prompt:".  
            - If the answer is explicitly stated in the "Context:", prioritize that information.  
            - If the answer is not directly stated but can be **reasonably inferred** using logical deduction from the provided "Context:" or "Fact Sheet:", do so.  
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

    def query_regulation(self, request):
        try:
            selected_regulation = self.__get_matching_regulation(request["regulation"])

            conversation = self.__regulation_repository.get_conversation(request["userId"], request["conversationId"]) if request["conversationId"] else None
            if not conversation:
                summarized_query = self.__ai_service.generate_title(request["query"], 30)
                conversation = self.__regulation_repository.create_conversation(request["userId"], summarized_query, request["regulation"])

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
                should_include_fact_sheet = self.__ai_service.should_pull_fact_sheet(request["query"], ai_formatted_conversation_history, selected_regulation)
                if should_include_fact_sheet:
                    fact_sheet = self.__regulation_repository.get_fact_sheet(selected_regulation)
                    fact_sheet = self.__ai_service.summarize_text(fact_sheet)

            directions = None
            response = None
            context = None
            context_summarized = None
            user_query = request["query"]
            improved_user_query = user_query
            if len(ai_formatted_conversation_history) > 0:
                improved_user_query = self.__ai_service.improve_query(user_query, ai_formatted_conversation_history)    
                logging.info(f'Improved Query: {improved_user_query}')
            else: 
                logging.info('Not improving query.  Not enough context to be of any assistance')
                
            # should_get_embeddings = self.__ai_service.should_pull_more_embeddings(improved_user_query, ai_formatted_conversation_history, selected_regulation)
            # if should_get_embeddings:
            generate_query_embeddings = self.__ai_service.generate_embeddings(improved_user_query)
            embeddings = self.__regulation_repository.query_embeddings(generate_query_embeddings, selected_regulation)
            if len(embeddings) == 0:
                logging.error("No matches found in vector database. Querying without additional embeddings")
                directions = self.__get_directions_without_context()
                response = self.__ai_service.call_without_context(
                    ai_formatted_conversation_history,
                    selected_regulation,
                    directions,
                    fact_sheet,
                    improved_user_query
                )
            else:
                directions = self.__get_directions_with_context()
                context = " ".join([i["text"] for i in embeddings])

                context_summarized = self.__ai_service.summarize_text(context)
                response = self.__ai_service.call_with_context(
                    context, 
                    ai_formatted_conversation_history, 
                    selected_regulation,
                    directions,
                    fact_sheet,
                    improved_user_query
                )
                    
            # else:
            #     directions = self.__get_directions_without_context()
            #     response = self.__ai_service.call_without_context(
            #         ai_formatted_conversation_history,
            #         selected_regulation,
            #         directions,
            #         fact_sheet,
            #         improved_user_query
            #     )

            self.__regulation_repository.save_conversation_log({
                "conversationId": conversation["id"],
                "userId": request["userId"],
                "promptRaw": user_query,
                "promptImproved": improved_user_query,
                "contextRaw": context,
                "contextSummarized": context_summarized,
                "factSheet": fact_sheet,
                "directions": directions,
                "response": response
            })

            return {
                "result": response,
                "conversationId": conversation["id"]
            }

        except Exception as e:
            logging.error(f"Error processing the query: {str(e)}")
            return None