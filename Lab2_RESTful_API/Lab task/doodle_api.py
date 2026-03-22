from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from uuid import uuid4

app = FastAPI(title="Doodle API", description="Simple voting API")

polls = {}


class PollCreate(BaseModel):
    title: str
    options: List[str]


class Poll(BaseModel):
    id: str
    title: str
    options: List[str]
    votes: Dict[str, int]


class Vote(BaseModel):
    option: str


@app.post("/polls", response_model=Poll)
async def create_poll(poll: PollCreate):
    poll_id = str(uuid4())
    new_poll = Poll(
        id=poll_id,
        title=poll.title,
        options=poll.options,
        votes={option: 0 for option in poll.options}
    )
    polls[poll_id] = new_poll
    return new_poll


@app.get("/polls", response_model=List[Poll])
async def list_polls():
    return list(polls.values())


@app.get("/polls/{poll_id}", response_model=Poll)
async def get_poll(poll_id: str):
    if poll_id not in polls:
        raise HTTPException(status_code=404, detail="Poll not found")
    return polls[poll_id]


@app.put("/polls/{poll_id}", response_model=Poll)
async def update_poll(poll_id: str, poll: PollCreate):
    if poll_id not in polls:
        raise HTTPException(status_code=404, detail="Poll not found")
    updated_poll = Poll(
        id=poll_id,
        title=poll.title,
        options=poll.options,
        votes={option: 0 for option in poll.options}
    )
    polls[poll_id] = updated_poll
    return updated_poll


@app.delete("/polls/{poll_id}")
async def delete_poll(poll_id: str):
    if poll_id not in polls:
        raise HTTPException(status_code=404, detail="Poll not found")
    del polls[poll_id]
    return {"message": "Poll deleted"}


@app.post("/polls/{poll_id}/vote")
async def cast_vote(poll_id: str, vote: Vote):
    if poll_id not in polls:
        raise HTTPException(status_code=404, detail="Poll not found")
    poll = polls[poll_id]
    if vote.option not in poll.votes:
        raise HTTPException(status_code=400, detail="Invalid option")
    poll.votes[vote.option] += 1
    return {"message": "Vote cast"}


@app.delete("/polls/{poll_id}/vote")
async def delete_vote(poll_id: str, vote: Vote):
    if poll_id not in polls:
        raise HTTPException(status_code=404, detail="Poll not found")
    poll = polls[poll_id]
    if vote.option not in poll.votes:
        raise HTTPException(status_code=400, detail="Invalid option")
    if poll.votes[vote.option] > 0:
        poll.votes[vote.option] -= 1
        return {"message": "Vote removed"}
    else:
        raise HTTPException(status_code=400, detail="No votes to remove for this option")


@app.get("/polls/{poll_id}/results", response_model=Dict[str, int])
async def get_results(poll_id: str):
    if poll_id not in polls:
        raise HTTPException(status_code=404, detail="Poll not found")
    return polls[poll_id].votes
