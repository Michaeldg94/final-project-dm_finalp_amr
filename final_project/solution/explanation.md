# Explanation


*This project is a Movie Recommendation API designed to manage movie-related data and generate recommendations for users.*



It handles movies, genres, user ratings, and the relationships between them, allowing users to retrieve movie information as well as receive personalized recommendations.*

The API follows a layered, modular architecture, which improves maintainability, testability, and scalability. Each layer has a clear responsibility within the application.

File paths within the codebase are included for reference (**Note**: they are all found under the server/ directory)

---
### Models - (models/)

These are the database entities, most likely implemented with SQLAlchemy.
They map directly to database tables such as:

- Movies

- Ratings

- Genres

- Users

- Movie-genre relationships

Some files like *_raw.py likely represent temporary or unprocessed data models used for ingestion or early processing.

---
### Schemas - (schemas/)

These are Pydantic schemas used for:

Validating incoming requests

Ensuring clean and safe API responses

Schemas act as a security and formatting layer between the database and the client.

---

### Routers - (routers/)

Routers define the public HTTP endpoints of the API.
For example:

> movie.py → Movie queries and CRUD operations

>ratings.py → Rating operations for users/movies

>recommendation.py → Endpoints that provide movie recommendations

These modules handle request routing but delegate business logic to the services layer.

---

### Services - (services/)

This layer contains business logic such as:

- Processing and validating input before interacting with the database

- Fetching filtered movie and rating data

- Generating recommendations based on user preferences or history

- Routers call services, and services call models — keeping responsibilities cleanly separated.

---

### Application Entry Point (app.py)

This file initializes the FastAPI app, registers routers, configures middleware, and boots the API.
It serves as the starting point for the backend server.

---


### Typical Request Flow

An example recommendation request follows this flow:

> Client Request → Router → Service → Models/Database
              → Schema-validated response → Client


## Movie APIs

*List of Movie APIs available for testing. A brief summary of design cosiderations are given under each*

---

### 1. Get list of movies - 
>GET (/movies)

>Example request with parameters:  
/movies?page=1&limit=10&search=animation

Parameters - page and limit.  Defaults set to 1 and 10 as per requirement.

Returns ALL movies and displays them given the page size( maximum number of records per page). Subsequent records can be accessed by incrementing page until the last record is reached.

---

*Optional Parameter: Search*

If a search parameter is included, a more complex query is run behind the scenes.

It consists of the following steps.

1. Create a subquery that joins movies, movies_genres and genres to access filtering by genre. 


Left outer join is used to return ALL movies - even those without any genre. It is deduplicated within the subquery using  the distinct keyword.

---

2. Still within the subquery, use SQL case when statements to award 'points' to each movie based on the following criteria

> case((func.lower(MovieModel.title) == search_lower, 5), else_=0)

Exact title matches get 5 points

> case((func.lower(MovieModel.title).like(search_term), 2), else_=0)

Movie titles containing the search term get 2 points

> case((func.lower(GenreModel.genre_name).like(search_term), 1), else_=0)

Movies with genres containing the search term get 1 point

----
3. In the outer query, join movies and the subquery and rank movies by points (ties ordered alphabetically). Finally applies pagination to ordered results

## API 2 - Get Avg Rating by Movie ID - 
>GET /movies/{movie_id}/avg-rating

Simple API that joins movie and ratings tables and performs a group by on the selected movie ID and averages the rating. Also returns how many ratings there are for each movie.


# Ratings APIs — Quick Overview

Implementation of the Ratings feature: router, schemas, and service layer.

---

## `server/routers/ratings.py`
FastAPI endpoints for Ratings.

- **RatingCreate:**
- >POST `/api/rest/v1/ratings`** — create a rating 
    ```json
    { "user_id": 1, "movie_id": 1, "rating": 2.0 }
    ```
  - **Response 201 (`RatingResponse`):**
    `{ rating_id, user_id, movie_id, rating, timestamp }`
  - **Errors:** 404 (movie/user), 409 (duplicate), 400 (validation)

- **RatingDelete:**
- >DELETE `/{user_id}/{movie_id}` — delete a rating  
  - **Response 200 (`RatingDelete`):**
    `{ user_id, movie_id, message }`
  - **Errors:** 404 (not found), 400 (validation)
- Uses dependency-injected SQLAlchemy `Session` via `get_db()`.

---

## `server/schemas/ratings.py`
Pydantic models (request/response).

- **`RatingCreate`**: payload to create a rating (`user_id`, `movie_id`, `rating` in [0.5–5.0]).
- **`RatingResponse`**: created rating with `rating_id` and UTC `timestamp`.
- **`RatingDelete`**: delete confirmation (`user_id`, `movie_id`, `message`).

---

## `server/services/ratings.py`
Business logic and data access.

- **`RatingService`**: thin service layer calling the data manager.
  - `create_rating(payload)` → validates and creates.
  - `delete_rating(user_id, movie_id)` → deletes by pair.
- **`RatingDataManager`**:
  - Validations: movie exists, user exists, **enforces one rating per `(user_id, movie_id)`**.
  - On create: sets UTC `timestamp`, commits; handles race conditions via `IntegrityError`.
  - On delete: selects by `(user_id, movie_id)`, raises `ValueError("Rating not found")` if missing; then deletes.

**Note:** Deleting by `(user_id, movie_id)` is safe because the pair is unique; `rating_id`/`timestamp` are not required for deletion.


# Recommendation Engine APIs – Developer Guide

This module adds a **trainable movie recommender** to our FastAPI app.  
It exposes a small REST surface, runs training **asynchronously** in the background, logs runs to **MLflow**, and serves **top-N recommendations** with normalized scores.

---

## Summary of Key Points

> POST `/api/rest/v1/recommendation-engine`:

- enqueue training (non-blocking) with `202 Accepted` and `{ task_id, status: "queued" }`

>GET** `/api/rest/v1/recommendation-engine/{task_id}`: 

- poll training job status or get run metadata

 >GET** `/api/rest/v1/user/{user_id}/recommended-movies?n=10`:

- returns top-N movie IDs + normalized scores

Under the hood:
- **Training**: prunes long tail, builds a **sparse CSR** user–item matrix, fits **NMF**, logs **W/H** and mappings to MLflow.
- **Inference**: loads **latest MLflow run**, scores either the user’s row (`W @ H`) or a popularity fallback, **min–max normalizes**, returns top-N.







