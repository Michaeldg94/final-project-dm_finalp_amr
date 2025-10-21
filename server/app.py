from fastapi import FastAPI

from .routers import movie

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello FastAPI"}


@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}


app.include_router(movie.router)
