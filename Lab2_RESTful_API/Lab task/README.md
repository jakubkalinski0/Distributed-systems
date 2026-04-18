# Doodle API

Simple voting API built with FastAPI.

## Features

- Create polls with multiple options
- Cast votes on polls
- View poll details and results
- Update and delete polls

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   uvicorn doodle_api:app --reload
   ```

3. Open Swagger UI at `http://localhost:8000/docs`

## API Endpoints

- `POST /polls` - Create a new poll
- `GET /polls` - List all polls
- `GET /polls/{id}` - Get poll details
- `PUT /polls/{id}` - Update poll
- `DELETE /polls/{id}` - Delete poll
- `POST /polls/{id}/vote` - Cast a vote
- `DELETE /polls/{id}/vote` - Remove a vote
- `GET /polls/{id}/results` - Get vote results