import os
import sys
import json
import re
import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from datenight import (
    get_gemini_client,
    get_anthropic_client,
    get_openai_client,
    resolve_date,
    fetch_events_json,
    parse_events,
    load_directory,
    save_directory,
    generate_html_file
)

app = FastAPI(title="Twin Cities Date Night API")

# Ensure static directory exists
os.makedirs("static", exist_ok=True)

# Record server start time for deployment verification
SERVER_START_TIME = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class Venue(BaseModel):
    name: str
    url: str
    type: str

class DiscoverRequest(BaseModel):
    custom_details: str = ""

class SearchRequest(BaseModel):
    date_query: str = ""


def discover_venues_api(client, directory, custom_details):
    """API-friendly version of venue discovery that returns the parsed JSON list of venues."""
    existing_names = [s["name"] for s in directory]
    
    if not custom_details:
        prompt_instructions = (
            "Discover new venues in the Twin Cities (Minneapolis and Saint Paul, MN) across these categories:\n"
            "- 'Media, Newspapers & Independent Aggregators'\n"
            "- 'Music Promoters, Clubs & Major Arenas'\n"
            "- 'Performing Arts & Prestigious Theaters'\n"
            "- 'Independent Cinema & Local Fairs'\n"
            "- Little-known, ethnic, or cultural theatre, music, and restaurants that host live events or have highly unique cultural dining experiences (standard dining-only restaurants are excluded).\n"
        )
    else:
        prompt_instructions = (
            "Discover new arts, culture, theatre, music, and dining venues in the Twin Cities (Minneapolis and Saint Paul, MN).\n"
            "Search for all venues you can, but especially focus on little-known, ethnic, or cultural theatre, music, and restaurants.\n"
            "For dining and restaurants, ONLY list venues that host live events, performances, or have something really unique and special going on (such as indigenous dining experiences, regular live music, cultural performances, or pop-up chef/event series)—do NOT list standard dining-only restaurants.\n"
            f"Additional search focus/requirements: '{custom_details}'.\n"
        )
    
    prompt = (
        f"{prompt_instructions}\n"
        f"The discovered venues must NOT be in this list of existing venues: {', '.join(existing_names)}.\n"
        "Return the discovered venues as a JSON list. Each venue object must have the following keys:\n"
        "- 'name': Name of the venue/restaurant\n"
        "- 'url': Official website URL\n"
        "- 'type': Category (assign to one of the category groupings above, or a similarly descriptive type)\n\n"
        "Ensure the output is valid JSON. Do not include any introductory or concluding text. Wrap the JSON in a markdown code block."
    )
    
    try:
        if not client:
            raise ValueError("Gemini client is not initialized")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                temperature=0.3,
            ),
        )
        return parse_events(response.text)
    except Exception as e:
        print(f"[Warning] Gemini venue discovery (API) failed: {e}. Falling back to Claude...")
        try:
            anthropic_client = get_anthropic_client()
            if anthropic_client:
                claude_prompt = (
                    f"You are a local Twin Cities concierge analyzer. Since you do not have live web search access, please use your pre-trained knowledge to discover new venues.\n"
                    f"{prompt_instructions}\n"
                    f"The discovered venues must NOT be in this list of existing venues: {', '.join(existing_names)}.\n"
                    "Return the discovered venues as a JSON list. Each venue object must have the following keys:\n"
                    "- 'name': Name of the venue/restaurant\n"
                    "- 'url': Official website URL\n"
                    "- 'type': Category (assign to one of the category groupings above, or a similarly descriptive type)\n\n"
                    "Ensure the output is valid JSON. Do not include any introductory or concluding text. Wrap the JSON in a markdown code block."
                )
                response = anthropic_client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=4000,
                    temperature=0.3,
                    messages=[{"role": "user", "content": claude_prompt}]
                )
                return parse_events(response.content[0].text)
        except Exception as claude_err:
            print(f"[Warning] Claude fallback venue discovery (API) failed: {claude_err}. Falling back to ChatGPT...")
            
        try:
            openai_client = get_openai_client()
            if openai_client:
                openai_prompt = (
                    f"You are a local Twin Cities concierge analyzer. Since you do not have live web search access, please use your pre-trained knowledge to discover new venues.\n"
                    f"{prompt_instructions}\n"
                    f"The discovered venues must NOT be in this list of existing venues: {', '.join(existing_names)}.\n"
                    "Return the discovered venues as a JSON list. Each venue object must have the following keys:\n"
                    "- 'name': Name of the venue/restaurant\n"
                    "- 'url': Official website URL\n"
                    "- 'type': Category (assign to one of the category groupings above, or a similarly descriptive type)\n\n"
                    "Ensure the output is valid JSON. Do not include any introductory or concluding text. Wrap the JSON in a markdown code block."
                )
                for model_name in ["gpt-5.4-mini", "gpt-4o-mini"]:
                    try:
                        response = openai_client.chat.completions.create(
                            model=model_name,
                            messages=[{"role": "user", "content": openai_prompt}],
                            max_tokens=4000,
                            temperature=0.3
                        )
                        return parse_events(response.choices[0].message.content)
                    except Exception as model_err:
                        print(f"[Warning] OpenAI model {model_name} failed: {model_err}")
        except Exception as openai_err:
            print(f"[Error] ChatGPT fallback venue discovery (API) failed: {openai_err}")
        return []


@app.get("/")
def get_index():
    """Serves the front-end dashboard with the current server start timestamp."""
    if os.path.exists("static/index.html"):
        with open("static/index.html") as f:
            html = f.read()
        html = html.replace("{{SERVER_START_TIME}}", SERVER_START_TIME)
        return HTMLResponse(html)
    return {"message": "Twin Cities Date Night API Running. Front-end static/index.html missing."}


@app.get("/api/venues")
def get_venues():
    """Retrieves all event venues from the local JSON store."""
    return load_directory()


@app.post("/api/venues")
def add_venue(venue: Venue):
    """Adds a new venue to the directory."""
    directory = load_directory()
    if any(v["name"].lower() == venue.name.lower() for v in directory):
        raise HTTPException(status_code=400, detail="Venue already exists.")
    new_v = {"name": venue.name, "url": venue.url, "type": venue.type}
    directory.append(new_v)
    save_directory(directory)
    return {"success": True, "directory": directory}


@app.delete("/api/venues")
def delete_venue(name: str):
    """Deletes a venue from the directory."""
    directory = load_directory()
    filtered = [v for v in directory if v["name"].lower() != name.lower()]
    if len(filtered) == len(directory):
        raise HTTPException(status_code=404, detail="Venue not found.")
    save_directory(filtered)
    return {"success": True, "directory": filtered}


@app.post("/api/venues/discover")
def discover_venues(req: DiscoverRequest):
    """Calls Gemini to find new venues based on custom search terms."""
    try:
        client = get_gemini_client()
        directory = load_directory()
        discovered = discover_venues_api(client, directory, req.custom_details)
        return discovered
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/events/search")
def search_events(req: SearchRequest):
    """Searches Twin Cities events on the given date and saves them in HTML format."""
    try:
        client = get_gemini_client()
        directory = load_directory()
        
        date_query = req.date_query.strip()
        if not date_query:
            date_query = datetime.date.today().strftime("%B %d, %Y")
            
        ccyymmdd = resolve_date(client, date_query)
        try:
            dt = datetime.datetime.strptime(ccyymmdd, "%Y%m%d")
            nice_date = dt.strftime("%A, %B %d, %Y")
        except Exception:
            nice_date = date_query
            
        json_text = fetch_events_json(client, date_query, directory)
        events = parse_events(json_text)
        
        filename = f"datenight.{ccyymmdd}.html"
        generate_html_file(events, nice_date, filename)
        
        return {
            "resolved_date": nice_date,
            "ccyymmdd": ccyymmdd,
            "html_filename": filename,
            "events": events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports/{filename}")
def get_report(filename: str):
    """Serves the generated HTML report file securely."""
    # Enforce secure naming pattern to prevent directory traversal
    if not re.match(r'^datenight\.\d{8}\.html$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename format.")
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(filename)


# Mount static assets directory
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    # Load .env variables for local run
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")
                    
    uvicorn.run(app, host="0.0.0.0", port=8000)
