from fastapi import APIRouter
from fastapi import status
import logging
from typing import Any, Optional
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from . import utils


router = APIRouter()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class MatchRequest(BaseModel):
    input: str


class SummarizeRequest(BaseModel):
    summary_question: Optional[str]

print(f"This is an example payload to send to /priors : {MatchRequest(input='').dict()}")
print(f"This is an example payload to send to /summarize : {SummarizeRequest(summary_question='What is the meaning of life?').dict()}")
print("""Eg: curl --header "Authorization:validated_user" -X POST http://localhost:8080/api/v1/summarize -d '{"summary_question":"blank"}' -H 'Content-Type: application/json'""")

@router.post("/priors", status_code=status.HTTP_200_OK)
def fetch_matches(request: MatchRequest):
     return JSONResponse(content={
        "success": True,
        "message": ["All matched data"]
    })

@router.post("/summarize", status_code=status.HTTP_200_OK)
def summarize(request: SummarizeRequest):

    docs = utils.get_similar_texts(request.summary_question)
    answer = utils.get_llm_response(docs)

    return JSONResponse(content={
        "success": True,
        "message": answer
    })


def dud():
    ...
