import azure.functions as func
import json
from mangers.regulation_manager import RegulationManager
from repositories.regulation_repository import RegulationRepository


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
    
@app.route(route="conversations/list", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def GetConversationListsAPI(req: func.HttpRequest) -> func.HttpResponse:
    req_body = req.get_json()

    user_id = req_body["userId"]
    
    if not user_id:
        return func.HttpResponse(
            "User Id is required",
            status_code=400
        )

    manager = RegulationManager()
    conversations = manager.get_conversations(user_id)

    return func.HttpResponse(
        json.dumps(conversations),
        status_code=200,
        mimetype="application/json"
    ) 

@app.route(route="conversations/load", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def GetConversationAPI(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        user_id = req_body.get("userId")
        conversation_id = req_body.get("conversationId")

        if not user_id:
            return func.HttpResponse("User Id is required", status_code=400)

        if not conversation_id:
            return func.HttpResponse("Conversation Id is required", status_code=400)

        repository = RegulationRepository()
        conversation = repository.get_conversation(user_id, conversation_id)

        if conversation is None:
            return func.HttpResponse("Conversation not found", status_code=404)

        return func.HttpResponse(
            json.dumps(conversation),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(
            f"Error retrieving conversation: {str(e)}",
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