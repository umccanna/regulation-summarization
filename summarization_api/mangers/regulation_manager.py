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
    
    def get_available_regulations(self):
        return self.__regulation_repository.get_available_regulations()

    def __convert_conversation_history_to_ai_format(self, conversation_log: list):
        converted_history = []

        for log in conversation_log:
            content_parts = [f'''
                {log["directions"]}

                Prompt: 
                {log["promptRaw"]}
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
            Only provide responses that can be found "Context:" provided below or from the "Context:" in any of the previous messages or any of your previous responses or any previous "Fact Sheet:" based on the user's "Prompt:" .  
            If you are unable to find a response in the below "Context:" or any previous message "Context:" or any of your previous respsonses or any previous "Fact Sheet:" do not make anything up.  Just response with "I'm not sure how to help you with that.  I may not have been designed to help with your request.".
            If a "Fact Sheet:" is provided use that content to inform and focus the response.
        '''
    
    def __get_directions_without_context(self):
        return '''
            Only provide responses that can be found in any previous message "Context:" or any previous message "Fact Sheet:" or any of previous your responses based on the user's "Prompt:".
            If you are unable to find a response in any previous message "Context:" or any previous message "Fact Sheet:" or any of your previous responses do not make anything up.  Just response with "I'm not sure how to help you with that.  I may not have been designed to help with your request.".
            If a "Fact Sheet:" is provided use that content to inform and focus the response. 
        '''

    def query_regulation(self, request):
        try:
            selected_regulation = self.__get_matching_regulation(request["regulation"])

            conversation = self.__regulation_repository.get_conversation(request["userId"], request["conversationId"]) if request["conversationId"] else None
            if not conversation:
                summarized_query = self.__ai_service.summarize_text(request["query"], 30)
                conversation = self.__regulation_repository.create_conversation(request["userId"], summarized_query, request["regulation"])

            ai_formatted_conversation_history = self.__convert_conversation_history_to_ai_format(conversation["log"])
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

            should_get_embeddings = self.__ai_service.should_pull_more_embeddings(request["query"], ai_formatted_conversation_history, selected_regulation)
            if should_get_embeddings:
                generate_query_embeddings = self.__ai_service.generate_embeddings(request["query"])
                embeddings = self.__regulation_repository.query_embeddings(generate_query_embeddings, selected_regulation)
                if len(embeddings) == 0:
                    logging.error("No matches found in vector database. Querying without additional embeddings")
                    directions = self.__get_directions_without_context()
                    response = self.__ai_service.call_without_context(
                        ai_formatted_conversation_history,
                        selected_regulation,
                        directions,
                        fact_sheet,
                        request["query"]
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
                        request["query"]
                    )
                    
            else:
                directions = self.__get_directions_without_context()
                response = self.__ai_service.call_without_context(
                    ai_formatted_conversation_history,
                    selected_regulation,
                    directions,
                    fact_sheet,
                    request["query"]
                )

            self.__regulation_repository.save_conversation_log({
                "conversationId": conversation["id"],
                "userId": request["userId"],
                "promptRaw": request["query"],
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