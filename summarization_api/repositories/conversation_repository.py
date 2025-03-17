import logging
from config import get_config
from azure.cosmos import CosmosClient
import uuid
from datetime import timezone 
import datetime 
from azure.cosmos.exceptions import CosmosResourceExistsError

class ConversationRepository:
    def __init__(self):
        self.__client = CosmosClient(get_config("COSMOS_DB_URL"), get_config("COSMOS_DB_KEY"))
        self.__database = self.__client.get_database_client(get_config("DATABASE_NAME"))

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
    
    def migrate_conversations(self, old_user_id, new_user_id):
        logging.info(f'Migrating conversations from {old_user_id} to {new_user_id}')

        container = self.__database.get_container_client("conversations")
        
        success = True
        for item in container.query_items(
            query = """
                SELECT *
                FROM c 
            """,
            partition_key=old_user_id
        ):
            try:
                if item["type"] == "Conversation":
                        container.create_item({
                            "id": item["id"],
                            "partitionKey": new_user_id,
                            "conversationName": item["conversationName"],
                            "regulationPartitionKey": item["regulationPartitionKey"],
                            "userId": new_user_id,
                            "type": "Conversation",
                            "created": item["created"],
                            "sequenceCount": item["sequenceCount"],
                            "updated": item["updated"]
                        })

                elif item["type"] == "ConversationLog":
                        container.create_item({
                            "id": item["id"],
                            "conversationId": item["conversationId"],
                            "partitionKey": new_user_id,
                            "promptRaw": item["promptRaw"] if "promptRaw" in item else None,
                            "promptImproved": item["promptImproved"] if "promptImproved" in item else None,
                            "contextRaw": item["contextRaw"],
                            "contextSummarized": item["contextSummarized"],
                            "factSheet": item["factSheet"],
                            "sequence": item["sequence"],
                            "directions": item["directions"] if "directions" in item else None,
                            "response": item["response"] if "response" in item else None,
                            "type": "ConversationLog",
                            "created": item["created"]
                        })
                else:
                    success = False
                    logging.warning(f"Conversation item skipped because type is unknown. Id: {item['id']}, Type: {item['type']}, partitionKey: {item['partitionKey']}")            
            except CosmosResourceExistsError:
                logging.warning(f"Item already exists in partition, ignoring.  Possibly from a previous migration. Id: {item['id']}, Type: {item['type']}, partitionKey: {item['partitionKey']}")

        return success
    
    def get_conversation(self, user_id: str, conversation_id: str):
        if not conversation_id:
            return None
        
        logging.info(f'Getting conversation by id {conversation_id} with latest 5 exchanges')

        container = self.__database.get_container_client("conversations")
        conversation_log = []
        for item in container.query_items(
            query="""
            SELECT 
                c.promptRaw, c.contextSummarized, c.factSheet, c.response, 
                c.directions, c.sequence, c.created, c.promptImproved
            FROM c 
            WHERE c.conversationId = @ConversationId 
            AND c.type = 'ConversationLog' 
            ORDER BY c.sequence DESC
            """,
            parameters=[{"name":"@ConversationId", "value": conversation_id}],
            partition_key=user_id
        ):
            conversation_log.append({
                "promptRaw": item["promptRaw"],
                "promptImproved": item["promptImproved"] if "promptImproved" in item else "",
                "contextSummarized": item["contextSummarized"],
                "factSheet": item["factSheet"],
                "response": item["response"] if "response" in item else "",
                "directions": item["directions"],
                "sequence": item["sequence"],
                "created": item["created"]
            })
        conversation_log.reverse()
        
        conversation_item = container.read_item(conversation_id, partition_key=user_id)
        return self.__convert_from_cosmos_conversation(conversation_item, conversation_log)
    
    def get_conversations(self, user_id: str):
        logging.info(f'Getting conversations for {user_id}')

        container = self.__database.get_container_client("conversations")
        conversations = []
        for item in container.query_items(
            query="SELECT TOP 20 * FROM c WHERE c.type = 'Conversation' AND (c.deleted = false OR NOT IS_DEFINED(c.deleted)) ORDER BY c.created DESC",
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
                "promptImproved": request["promptImproved"],
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

        