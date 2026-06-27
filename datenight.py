import os
import sys
import json
import re
import datetime
import urllib.parse
from google import genai
from google.genai import types
import anthropic
import openai

# Initial core list of Twin Cities event sources
DEFAULT_DIRECTORY = [
    {"name": "Racket MN", "url": "racketmn.com", "type": "Independent Media"},
    {"name": "Mpls.St.Paul Magazine", "url": "mspmag.com", "type": "Magazine"},
    {
        "name": "First Avenue & Venues",
        "url": "first-avenue.com",
        "type": "Music Promoter",
    },
    {
        "name": "AXS Minneapolis",
        "url": "axs.com/MN-Minneapolis/browse",
        "type": "Ticketing/Promoter",
    },
    {
        "name": "Hennepin Arts (Orpheum/State)",
        "url": "hennepinarts.org",
        "type": "Theater/Broadway",
    },
    {"name": "Penumbra Theatre", "url": "penumbratheatre.org", "type": "Theater"},
    {"name": "Mixed Blood Theatre", "url": "mixedblood.com", "type": "Theater"},
    {"name": "Minnesota Opera", "url": "mnopera.org", "type": "Classical/Opera"},
    {
        "name": "Minnesota Orchestra",
        "url": "minnesotaorchestra.org",
        "type": "Classical",
    },
    {
        "name": "St. Paul Chamber Orchestra (SPCO)",
        "url": "thespco.org",
        "type": "Classical",
    },
    {
        "name": "MSP Film Society (The Main)",
        "url": "mspfilm.org",
        "type": "Independent Cinema",
    },
    {"name": "Trylon Cinema", "url": "trylon.org", "type": "Independent Cinema"},
]


def save_directory(directory, filename="venues.json"):
    """Saves the venue directory to a local JSON file."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(directory, f, indent=4)
    except Exception as e:
        print(f"Error saving venue directory: {e}")


def load_directory(filename="venues.json"):
    """Loads the venue directory from a local JSON file. Falls back to default if the file is missing or invalid."""
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading venue directory: {e}. Falling back to default list.")
    
    # If the file doesn't exist or failed to load, populate it with the defaults
    save_directory(DEFAULT_DIRECTORY, filename)
    return DEFAULT_DIRECTORY.copy()


def load_env_keys():
    """Loads API keys from .env if they are not already in environment variables."""
    if os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            k = parts[0].strip()
                            v = parts[1].strip().strip('"').strip("'")
                            if k not in os.environ:
                                os.environ[k] = v
        except Exception as e:
            print(f"[Warning] Failed to read .env file: {e}")
    
    # Standardize Anthropic key
    if "CLAUDE_API_KEY" in os.environ and "ANTHROPIC_API_KEY" not in os.environ:
        os.environ["ANTHROPIC_API_KEY"] = os.environ["CLAUDE_API_KEY"]


def get_anthropic_client():
    """Initializes the Anthropic client using environment variables or a local .env file."""
    load_env_keys()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        return anthropic.Anthropic(api_key=api_key)
    except Exception as e:
        print(f"[Warning] Failed to initialize Anthropic client: {e}")
        return None


def get_openai_client():
    """Initializes the OpenAI client using environment variables or a local .env file."""
    load_env_keys()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        return openai.OpenAI(api_key=api_key)
    except Exception as e:
        print(f"[Warning] Failed to initialize OpenAI client: {e}")
        return None


def get_gemini_client():
    """Initializes the Gemini client using environment variables or a local .env file."""
    load_env_keys()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[Warning] GEMINI_API_KEY not found in environment or .env file.")
        return None
    try:
        return genai.Client()
    except Exception as e:
        print(f"[Warning] Failed to initialize Gemini client: {e}")
        return None


def discover_venues_via_gemini(client, directory):
    """Uses Gemini to find new ethnic/cultural/under-represented venues and adds selected ones to the directory."""
    print("\n--- Discover New Venues via Gemini ---")
    custom_details = input(
        "Specify any additional details (e.g., focus on theaters/music, specific locations, venue/event types)\n"
        "or press Enter to perform a general search: "
    ).strip()

    print("\nQuerying Gemini for new Twin Cities cultural venues, theatres, and restaurants...")
    
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
    
    json_text = None
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
        json_text = response.text
    except Exception as e:
        print(f"[Warning] Gemini venue discovery failed: {e}. Falling back to Claude...")
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
                json_text = response.content[0].text
        except Exception as claude_err:
            print(f"[Warning] Claude fallback venue discovery failed: {claude_err}. Falling back to ChatGPT...")

    if not json_text:
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
                        json_text = response.choices[0].message.content
                        break
                    except Exception as model_err:
                        print(f"[Warning] OpenAI model {model_name} failed: {model_err}")
        except Exception as openai_err:
            print(f"[Error] ChatGPT fallback venue discovery failed: {openai_err}")

    if not json_text:
        print("An error occurred during venue discovery: both Gemini and Claude failed.")
        return

    try:
        # Parse JSON
        match = re.search(r'```json\s*(.*?)\s*```', json_text, re.DOTALL)
        if match:
            content = match.group(1)
        else:
            start = json_text.find('[')
            end = json_text.rfind(']')
            if start != -1 and end != -1:
                content = json_text[start:end+1]
            else:
                content = json_text
                
        venues = json.loads(content)
        
        if not venues or not isinstance(venues, list):
            print("No new venues found or failed to parse the response.")
            return

        print("\n--- Discovered Venues ---")
        for idx, v in enumerate(venues, start=1):
            print(f"{idx}. {v['name']} ({v['url']}) [{v['type']}]")
            
        print("\nOptions:")
        print("Enter numbers separated by commas to add (e.g., '1,3,5')")
        print("[A] Add all discovered venues")
        print("[C] Cancel and return")
        
        choice = input("Select an option: ").strip().lower()
        if choice == 'c':
            print("Cancelled.")
            return
        elif choice == 'a':
            added_count = 0
            for v in venues:
                if v['name'] not in [ex['name'] for ex in directory]:
                    directory.append(v)
                    added_count += 1
            if added_count > 0:
                save_directory(directory)
            print(f"Successfully added {added_count} venues!")
        else:
            try:
                indices = [int(i.strip()) - 1 for i in choice.split(",") if i.strip().isdigit()]
                added_count = 0
                for idx in indices:
                    if 0 <= idx < len(venues):
                        v = venues[idx]
                        if v['name'] not in [ex['name'] for ex in directory]:
                            directory.append(v)
                            added_count += 1
                if added_count > 0:
                    save_directory(directory)
                print(f"Successfully added {added_count} venues!")
            except Exception:
                print("Invalid input format.")
                
    except Exception as e:
        print(f"An error occurred during venue discovery: {e}")


def manage_directory(client, directory):
    """Allows manual updates (additions/deletions) to the source directory, including Gemini discovery."""
    while True:
        print("\n--- Current Twin Cities Event Directory ---")
        for idx, source in enumerate(directory, start=1):
            print(f"{idx}. {source['name']} ({source['url']}) [{source['type']}]")

        print("\nOptions:")
        print("[A] Add a new source")
        print("[D] Delete a source")
        print("[G] Discover new venues via Gemini")
        print("[M] Main Menu (Done modifying)")

        choice = input("Select an option (A/D/G/M): ").strip().upper()

        if choice == "A":
            name = input("Enter source/venue name: ").strip()
            url = input("Enter website URL: ").strip()
            category = input(
                "Enter category (e.g., Theater, Music, Festival): "
            ).strip()

            if name and url:
                print(f"\nConfirm adding: {name} | {url} ({category})")
                confirm = input("Proceed? (y/n): ").strip().lower()
                if confirm == "y":
                    directory.append({"name": name, "url": url, "type": category})
                    save_directory(directory)
                    print("Source added successfully!")
            else:
                print("Invalid input. Name and URL are required.")

        elif choice == "D":
            try:
                idx_to_del = (
                    int(input("Enter the number of the source to delete: ")) - 1
                )
                if 0 <= idx_to_del < len(directory):
                    target = directory[idx_to_del]
                    print(f"\nConfirm DELETING: {target['name']}")
                    confirm = input("Are you absolutely sure? (y/n): ").strip().lower()
                    if confirm == "y":
                        directory.pop(idx_to_del)
                        save_directory(directory)
                        print("Source removed successfully.")
                else:
                    print("Invalid index number.")
            except ValueError:
                print("Please enter a valid number.")

        elif choice == "G":
            discover_venues_via_gemini(client, directory)

        elif choice == "M":
            break
        else:
            print("Invalid selection. Try again.")


def resolve_date(client, date_query):
    """Resolves the user's date query to YYYYMMDD format using Gemini, falling back to Claude, then OpenAI if necessary."""
    today = datetime.date.today().strftime("%B %d, %Y")
    prompt = (
        f"Today is {today}. Parse the following date description: '{date_query}' and resolve it to a specific calendar date. "
        f"Return ONLY the date in YYYYMMDD format (8 digits, e.g., 20260626) with no other text, markdown, or characters. "
        f"If you cannot determine the date, return the current date in YYYYMMDD format."
    )
    # 1. Gemini
    try:
        if not client:
            raise ValueError("Gemini client is not initialized")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        resolved = response.text.strip()
        match = re.search(r'\d{8}', resolved)
        if match:
            return match.group(0)
        return datetime.date.today().strftime("%Y%m%d")
    except Exception as e:
        print(f"[Warning] Gemini date resolution failed: {e}. Falling back to Claude...")
        
    # 2. Claude
    try:
        anthropic_client = get_anthropic_client()
        if anthropic_client:
            response = anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=20,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}]
            )
            resolved = response.content[0].text.strip()
            match = re.search(r'\d{8}', resolved)
            if match:
                return match.group(0)
    except Exception as claude_err:
        print(f"[Warning] Claude fallback date resolution failed: {claude_err}. Falling back to ChatGPT...")
        
    # 3. ChatGPT
    try:
        openai_client = get_openai_client()
        if openai_client:
            for model_name in ["gpt-5.4-mini", "gpt-4o-mini"]:
                try:
                    response = openai_client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=20,
                        temperature=0.0
                    )
                    resolved = response.choices[0].message.content.strip()
                    match = re.search(r'\d{8}', resolved)
                    if match:
                        return match.group(0)
                    break
                except Exception as model_err:
                    print(f"[Warning] OpenAI model {model_name} failed: {model_err}")
    except Exception as openai_err:
        print(f"[Error] ChatGPT fallback date resolution failed: {openai_err}")
        
    return datetime.date.today().strftime("%Y%m%d")


def fetch_events_json(client, date_query, directory):
    """Queries Gemini with Search grounding to return events in JSON format, falling back to Claude, then OpenAI if necessary."""
    sources_context = ", ".join([s["name"] for s in directory])
    
    prompt = (
        f"You are a local Twin Cities concierge analyzer. Find and list public events happening on the date: '{date_query}'.\n"
        f"Prioritize monitoring key venues and frameworks mentioned here: {sources_context}.\n"
        f"Return the events as a JSON array (list). Each event object in the list MUST have the following keys:\n"
        f"- 'name': The name of the event\n"
        f"- 'venue': The venue or location\n"
        f"- 'time': The time of the event\n"
        f"- 'details': A brief details/description of the event\n"
        f"- 'link': A URL to buy tickets or get more info. If you find a website link for the event or venue in your search grounding/results, use it. Otherwise, use an official website of the venue.\n\n"
        f"Ensure the output is valid JSON. Do not include any introductory or concluding text. Wrap the JSON in a markdown code block if needed."
    )
    
    # 1. Gemini
    try:
        if not client:
            raise ValueError("Gemini client is not initialized")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                temperature=0.2,
            ),
        )
        return response.text
    except Exception as e:
        print(f"[Warning] Gemini event retrieval failed: {e}. Falling back to Claude...")
        
    offline_prompt = (
        f"You are a local Twin Cities concierge analyzer. Since you do not have live web search access, please use your pre-trained knowledge to generate a list of typical resident events, weekly shows, or seasonal festivals/events happening on the date '{date_query}' at these venues: {sources_context}.\n"
        f"If a specific date is given, estimate what events would typically be scheduled on that day of the week or season at those venues.\n"
        f"Return the events as a JSON array (list). Each event object in the list MUST have the following keys:\n"
        f"- 'name': The name of the event\n"
        f"- 'venue': The venue or location\n"
        f"- 'time': The time of the event\n"
        f"- 'details': A brief details/description of the event\n"
        f"- 'link': A URL to buy tickets or get more info (an official website of the venue or event page).\n\n"
        f"Ensure the output is valid JSON. Do not include any introductory or concluding text. Wrap the JSON in a markdown code block if needed."
    )
    
    # 2. Claude
    try:
        anthropic_client = get_anthropic_client()
        if anthropic_client:
            response = anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4000,
                temperature=0.2,
                messages=[{"role": "user", "content": offline_prompt}]
            )
            return response.content[0].text
    except Exception as claude_err:
        print(f"[Warning] Claude fallback event retrieval failed: {claude_err}. Falling back to ChatGPT...")
        
    # 3. ChatGPT
    try:
        openai_client = get_openai_client()
        if openai_client:
            for model_name in ["gpt-5.4-mini", "gpt-4o-mini"]:
                try:
                    response = openai_client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": offline_prompt}],
                        max_tokens=4000,
                        temperature=0.2
                    )
                    return response.choices[0].message.content
                except Exception as model_err:
                    print(f"[Warning] OpenAI model {model_name} failed: {model_err}")
    except Exception as openai_err:
        print(f"[Error] ChatGPT fallback event retrieval failed: {openai_err}")
    return "```json\n[]\n```"


def parse_events(json_text):
    """Extracts and parses JSON array from LLM responses, cleaning up formatting anomalies."""
    if not json_text:
        return []
    
    # Try parsing directly if it is clean JSON
    try:
        return json.loads(json_text.strip())
    except json.JSONDecodeError:
        pass

    match = re.search(r'```json\s*(.*?)\s*```', json_text, re.DOTALL)
    if match:
        content = match.group(1)
    else:
        # Check if there is a general code block
        match_block = re.search(r'```\s*(.*?)\s*```', json_text, re.DOTALL)
        if match_block:
            content = match_block.group(1)
        else:
            start = json_text.find('[')
            end = json_text.rfind(']')
            if start != -1 and end != -1:
                content = json_text[start:end+1]
            else:
                content = json_text
    
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            # Remove trailing commas inside arrays or objects:
            # e.g., ,} -> } or ,] -> ]
            cleaned = re.sub(r',\s*([\]}])', r'\1', content)
            return json.loads(cleaned)
        except Exception:
            return []


def generate_html_file(events, nice_date, filename):
    """Generates a responsive, beautifully styled HTML event showcase."""
    events_html = ""
    if not events:
        events_html = """
        <div class="event-card" style="grid-column: 1 / -1; align-items: center; text-align: center;">
            <h2 class="event-name">No events found for this date.</h2>
            <p class="event-details">Please try another date search or verify event listings.</p>
        </div>
        """
    else:
        for event in events:
            name = event.get('name', 'Unnamed Event')
            venue = event.get('venue', 'Unknown Venue')
            time = event.get('time', 'See website')
            details = event.get('details', 'No details provided.')
            link = event.get('link', '')
            
            if not link:
                search_q = urllib.parse.quote(f"{name} {venue} Twin Cities")
                link = f"https://www.google.com/search?q={search_q}"
            
            events_html += f"""
            <div class="event-card">
                <div class="event-info-top">
                    <span class="venue-tag">{venue}</span>
                    <h2 class="event-name">{name}</h2>
                    <div class="time-location">
                        <div>
                            <svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" stroke="currentColor" fill="none" stroke-width="2"/></svg>
                            <span>{venue}</span>
                        </div>
                        <div>
                            <svg viewBox="0 0 24 24"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z" stroke="currentColor" fill="none" stroke-width="2"/></svg>
                            <span>{time}</span>
                        </div>
                    </div>
                    <p class="event-details">{details}</p>
                </div>
                <a href="{link}" target="_blank" rel="noopener noreferrer" class="action-button">
                    <span>More Info</span>
                    <svg viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" fill="none" stroke-width="2.5"/></svg>
                </a>
            </div>
            """
            
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Twin Cities Date Night - {nice_date}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0c10;
            --card-bg: rgba(25, 27, 38, 0.65);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-primary: #f5f6f9;
            --text-secondary: #a0aec0;
            --accent-glow: linear-gradient(135deg, #ff007f 0%, #7f00ff 100%);
            --accent-color: #bb86fc;
            --accent-hover: #cfb9fc;
            --neon-pink: #ff2a85;
            --neon-blue: #00f0ff;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #0f172a 50%, #020617 100%);
            color: var(--text-primary);
            font-family: 'Outfit', sans-serif;
            min-height: 100vh;
            padding: 2rem 1.5rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        .container {{
            max-width: 1200px;
            width: 100%;
        }}

        header {{
            text-align: center;
            margin-bottom: 3.5rem;
            position: relative;
        }}

        .logo-area {{
            display: inline-flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
        }}

        h1 {{
            font-size: 2.8rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--neon-blue) 0%, var(--neon-pink) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.03em;
            text-transform: uppercase;
            text-shadow: 0 0 40px rgba(0, 240, 255, 0.15);
        }}

        .date-badge {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.12);
            padding: 0.5rem 1.5rem;
            border-radius: 9999px;
            font-weight: 500;
            font-size: 1.1rem;
            color: var(--neon-blue);
            margin-top: 1rem;
            display: inline-block;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            letter-spacing: 0.05em;
            backdrop-filter: blur(8px);
        }}

        .events-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 2rem;
            width: 100%;
        }}

        .event-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            overflow: hidden;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            backdrop-filter: blur(16px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }}

        .event-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: var(--accent-glow);
            opacity: 0.8;
            transition: height 0.3s ease;
        }}

        .event-card:hover {{
            transform: translateY(-8px);
            border-color: rgba(255, 255, 255, 0.2);
            box-shadow: 0 20px 40px rgba(127, 0, 255, 0.15), 0 0 20px rgba(0, 240, 255, 0.1);
        }}

        .event-card:hover::before {{
            height: 6px;
        }}

        .event-info-top {{
            margin-bottom: 1.5rem;
        }}

        .venue-tag {{
            display: inline-block;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--neon-pink);
            margin-bottom: 0.75rem;
        }}

        .event-name {{
            font-size: 1.4rem;
            font-weight: 600;
            line-height: 1.3;
            color: var(--text-primary);
            margin-bottom: 0.75rem;
        }}

        .time-location {{
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-bottom: 1.25rem;
        }}

        .time-location div {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .time-location svg {{
            width: 16px;
            height: 16px;
            fill: none;
            stroke: currentColor;
            stroke-width: 2;
        }}

        .event-details {{
            font-size: 0.95rem;
            line-height: 1.6;
            color: rgba(245, 246, 249, 0.8);
            margin-bottom: 2rem;
        }}

        .action-button {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            border-radius: 12px;
            font-weight: 600;
            text-decoration: none;
            color: #fff;
            background: linear-gradient(135deg, rgba(255, 0, 127, 0.2) 0%, rgba(127, 0, 255, 0.2) 100%);
            border: 1px solid rgba(255, 255, 255, 0.15);
            transition: all 0.3s ease;
            width: 100%;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }}

        .action-button:hover {{
            background: var(--accent-glow);
            border-color: transparent;
            box-shadow: 0 10px 25px rgba(127, 0, 255, 0.4);
            transform: translateY(-1px);
        }}

        .action-button svg {{
            width: 16px;
            height: 16px;
            fill: none;
            stroke: currentColor;
            stroke-width: 2.5;
            transition: transform 0.2s ease;
        }}

        .action-button:hover svg {{
            transform: translateX(4px);
        }}

        .footer {{
            margin-top: 5rem;
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-secondary);
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 2rem;
            width: 100%;
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 1.5rem 1rem;
            }}
            h1 {{
                font-size: 2.2rem;
            }}
            .events-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-area">
                <h1>Twin Cities Date Night</h1>
                <div class="date-badge">{nice_date}</div>
            </div>
        </header>

        <div class="events-grid">
            {events_html}
        </div>

        <footer class="footer">
            <p>Date Night! &bull; Copyright John Bartucz</p>
        </footer>
    </div>
</body>
</html>"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)


def search_events_by_date(client, directory):
    """Uses Google Search grounding through Gemini to find live events on a specific date, outputs event details, and writes an HTML file."""
    print("\n--- Look Up Events By Date ---")
    today_str = datetime.date.today().strftime("%B %d, %Y")
    date_query = input(
        f"Enter a date (e.g., 'Tonight', 'This Saturday') [Default: {today_str}]: "
    ).strip()

    if not date_query:
        date_query = today_str

    print("Resolving date query...")
    ccyymmdd = resolve_date(client, date_query)
    try:
        dt = datetime.datetime.strptime(ccyymmdd, "%Y%m%d")
        nice_date = dt.strftime("%A, %B %d, %Y")
    except Exception:
        nice_date = date_query

    print(f"Date resolved to: {nice_date} ({ccyymmdd})")

    print(f"\nQuerying live data streams via Gemini for '{date_query}'...")
    try:
        json_text = fetch_events_json(client, date_query, directory)
        events = parse_events(json_text)

        print(f"\n=== Events Scheduled for {nice_date} ===")
        if not events:
            print("No events found or failed to parse events from response.")
        else:
            for idx, event in enumerate(events, start=1):
                name = event.get('name', 'Unnamed Event')
                venue = event.get('venue', 'Unknown Venue')
                time = event.get('time', 'See website')
                details = event.get('details', '')
                link = event.get('link', '')
                print(f"{idx}. {name}")
                print(f"   Venue: {venue}")
                print(f"   Time:  {time}")
                print(f"   Info:  {details}")
                if link:
                    print(f"   Link:  {link}")
                print()
        print("=========================================")

        # Save HTML file as datenight.[ccyymmdd].html
        filename = f"datenight.{ccyymmdd}.html"
        generate_html_file(events, nice_date, filename)
        print(f"\n[Success] Output HTML file created: {filename}")

    except Exception as e:
        print(f"An error occurred while gathering event data: {e}")


def main():
    client = get_gemini_client()
    directory = load_directory()

    while True:
        print("\n=========================================")
        print("    Twin Cities Event Portal Console     ")
        print("=========================================")
        print("1. View & Update Calendar Source List")
        print("2. Search Events on a Specific Date")
        print("3. Exit")

        main_choice = input("Select an option (1-3): ").strip()

        if main_choice == "1":
            manage_directory(client, directory)
        elif main_choice == "2":
            search_events_by_date(client, directory)
        elif main_choice == "3":
            print("Exiting application. Have a great day in the Twin Cities!")
            break
        else:
            print("Invalid choice. Enter 1, 2, or 3.")


if __name__ == "__main__":
    main()
