import logging
from config import get_config
from azure.cosmos import CosmosClient

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
                    "hasFACTSheet": regulation["hasFACTSheet"],
                    "hierarchies":regulation["hierarchies"]
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