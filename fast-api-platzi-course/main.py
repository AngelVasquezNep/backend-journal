import os
from enum import Enum

from pydantic import BaseModel, Field, EmailStr

from typing import Optional
from fastapi import FastAPI, Body, Query, Path

ENV = os.environ.get("ENV")
DEBUG = ENV != "production"

app = FastAPI(
    debug=DEBUG,
)


class AccountType(Enum):
    FREE = "FREE"
    SUBSCRIPTION = "SUBSCRIPTION"


class User(BaseModel):
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=150
    )
    age: Optional[int] = Field(
        default=None,
    )
    account_type: AccountType = Field(...)
    email: EmailStr = Field(...)


class Location(BaseModel):
    country: str


@app.get("/")
def home():
    return {
        "message": "Hello world",
    }


@app.post("/user")
def user(user: User = Body(...)):
    return user


@app.get("/user")
def user(
        full_name: str = Query(default=None, min_lenght=1, max_lenght=50),
        age: int = Query(...),
):
    return {
        "full_name": full_name,
        "age": age,
    }


@app.get("/user/{user_id}")
def user(user_id: int = Path(..., gt=0)):
    return {
        "user_id": user_id
    }


@app.put("/user/{user_id}")
def user(
    user_id: int = Path(...),
    user: User = Body(...),
    location: Location = Body(...)
):
    return {
        "user": user,
        "location": location
    }
