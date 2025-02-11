import logging
from config import get_config
from azure.cosmos import CosmosClient
import uuid
from datetime import timezone 
import datetime 

class RegulationRepository:
    def __init__(self):
        self.__client = CosmosClient(get_config("COSMOS_DB_URL"), get_config("COSMOS_DB_KEY"))
        self.__database = self.__client.get_database_client(get_config("DATABASE_NAME"))

    def get_available_regulations(self):
        available_regulations = []

        container = self.__database.get_container_client("pricingregulations")
        for item in container.query_items(
            query="SELECT TOP 1 c.regulations FROM c WHERE c.id = 'SupportedRegulations'",
            parameters=[],
            partition_key=f'Default'
        ):
            for regulation in item["regulations"]:
                available_regulations.append({
                    "partitionKey": regulation["partitionKey"],
                    "title": regulation["title"],
                    "hasFACTSheet": regulation["hasFACTSheet"]
                })

        return available_regulations
    
    def get_fact_sheet(self, regulation):        
        partition_key = regulation["partitionKey"]
        has_fact_sheet = regulation["hasFACTSheet"]
        if not has_fact_sheet:
            return None

        container = self.__database.get_container_client("pricingregulations")
        items = []

        logging.info('Getting fact sheet')

        for item in container.query_items(
            query="SELECT TOP 15 c.id, c.modelType, c.text, c.pageIndex, c.documentType FROM c WHERE c.documentType = 'FactSheet' ORDER BY c.pageIndex ASC",
            parameters=[],
            partition_key=partition_key
        ):
            items.append({
                "id": item["id"],
                "modelType": item["modelType"],
                "text": item["text"].encode("utf-8").decode("utf-8"),
                "documentType": item["documentType"]
            })

        return ' '.join([e["text"] for e in items])
    
    
    def query_embeddings(self, embeddings: list[float], regulation):
        if not regulation:
            return []
        
        logging.info("Searching Embeddings")
        
        partition_key = regulation["partitionKey"]
        container = self.__database.get_container_client("pricingregulations")
        items = []
        for item in container.query_items(
            query="SELECT TOP 10 c.id, c.modelType, c.text, c.pageIndex, c.documentType, VectorDistance(c.vector, @embedding) as similiarityScore FROM c ORDER BY VectorDistance(c.vector, @embedding)",
            parameters=[dict(
                name="@embedding", value=embeddings
            )],
            partition_key= partition_key
        ):
            items.append({
                "id": item["id"],
                "modelType": item["modelType"],
                "text": item["text"].encode("utf-8").decode("utf-8"),
                "documentType": item["documentType"],
                "similiarityScore": item["similiarityScore"]
            })

        logging.info(f'Embedding results found {len(items)}')
        return items    
    
    def __convert_from_cosmos_conversation(self, cosmos_conversation, log = None):
        return {
            "id": cosmos_conversation["id"],
            "regulation": cosmos_conversation["regulationPartitionKey"],
            "userId": cosmos_conversation["userId"],
            "name": cosmos_conversation["conversationName"],
            "log": log if log is not None else [],
            "created": cosmos_conversation["created"],
            "updated": cosmos_conversation["updated"] if "updated" in cosmos_conversation else None,
            "sequenceCount": cosmos_conversation["sequenceCount"]
        }
    
    def create_conversation(self, user_id: str, title: str, regulation: str):
        logging.info(f'Creating conversation for {user_id}')

        conversation_id = str(uuid.uuid4())
        container = self.__database.get_container_client("conversations")
        new_conversation = {
            "id": conversation_id,
            "partitionKey": user_id,
            "conversationName": title,
            "regulationPartitionKey": regulation,
            "userId": user_id,
            "type": "Conversation",
            "created": str(datetime.datetime.now(timezone.utc)),
            "sequenceCount": 0,
            "updated": None
        }
        container.create_item(new_conversation)

        return self.__convert_from_cosmos_conversation(new_conversation)
    
    def get_conversation(self, user_id: str, conversation_id: str):
        if not conversation_id:
            return None
        
        logging.info(f'Getting conversation by id {conversation_id}')

        container = self.__database.get_container_client("conversations")
        conversation_log = []
        for item in container.query_items(
            query="SELECT c.promptRaw, c.contextSummarized, c.factSheet, c.response, c.directions, c.sequence, c.created FROM c WHERE c.conversationId = @ConversationId AND c.type = 'ConversationLog' ORDER BY c.sequence ASC",
            parameters=[{"name":"@ConversationId", "value": conversation_id}],
            partition_key=user_id
        ):
            conversation_log.append({
                "promptRaw": item["promptRaw"],
                "contextSummarized": item["contextSummarized"],
                "factSheet": item["factSheet"],
                "response": item["response"],
                "directions": item["directions"],
                "sequence": item["sequence"],
                "created": item["created"]
            })
        
        conversation_item = container.read_item(conversation_id, partition_key=user_id)
        return self.__convert_from_cosmos_conversation(conversation_item, conversation_log)
    
    def get_conversations(self, user_id: str):
        logging.info(f'Getting conversations for {user_id}')

        container = self.__database.get_container_client("conversations")
        conversations = []
        for item in container.query_items(
            query="SELECT TOP 20 * FROM c WHERE c.type = 'Conversation' AND (c.deleted = false OR NOT IS_DEFINED(c.deleted)) ORDER BY c.created ASC",
            parameters=[],
            partition_key=user_id
        ):
            conversations.append(self.__convert_from_cosmos_conversation(item))
        
        return conversations
    
    def save_conversation_log(self, request):
        logging.info('Saving conversation log')

        container = self.__database.get_container_client("conversations")        
        conversation_item = container.read_item(request["conversationId"], partition_key=request["userId"])
        log_id = str(uuid.uuid4())
        patch_operation = ("patch", (request["conversationId"], [
            {
                "op": "set",
                "path": "/sequenceCount",
                "value": conversation_item["sequenceCount"]+1
            },
            {
                "op": "set",
                "path": "/updated",
                "value": str(datetime.datetime.now(timezone.utc))
            }
            ]), {})
        create_operation = ("create", ({
                "id": log_id,
                "conversationId": request["conversationId"],
                "partitionKey": request["userId"],
                "promptRaw": request["promptRaw"],
                "contextRaw": request["contextRaw"],
                "contextSummarized": request["contextSummarized"],
                "factSheet": request["factSheet"],
                "sequence": conversation_item["sequenceCount"]+1,
                "directions": request["directions"],
                "response": request["response"],
                "type": "ConversationLog",
                "created": str(datetime.datetime.now(timezone.utc))
            }, ), {})
        logging.info(f'Patch operation {patch_operation}')
        batch_operations = [
            patch_operation,
            create_operation
        ]

        container.execute_item_batch(batch_operations, partition_key=request["userId"])

        