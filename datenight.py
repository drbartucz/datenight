import os
import sys
from google import genai
from google.genai import types

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


def get_gemini_client():
    """Initializes the Gemini client using environment variables."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("\n[Error] GEMINI_API_KEY environment variable not found.")
        print("Please set it using: export GEMINI_API_KEY='your_key'")
        sys.exit(1)
    return genai.Client()


def manage_directory(directory):
    """Allows manual updates (additions/deletions) to the source directory."""
    while True:
        print("\n--- Current Twin Cities Event Directory ---")
        for idx, source in enumerate(directory, start=1):
            print(f"{idx}. {source['name']} ({source['url']}) [{source['type']}]")

        print("\nOptions:")
        print("[A] Add a new source")
        print("[D] Delete a source")
        print("[M] Main Menu (Done modifying)")

        choice = input("Select an option (A/D/M): ").strip().upper()

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
                        print("Source removed successfully.")
                else:
                    print("Invalid index number.")
            except ValueError:
                print("Please enter a valid number.")

        elif choice == "M":
            break
        else:
            print("Invalid selection. Try again.")


def search_events_by_date(client, directory):
    """Uses Google Search grounding through Gemini to find live events on a specific date."""
    print("\n--- Look Up Events By Date ---")
    date_query = input(
        "Enter a date (e.g., 'June 26, 2026', 'Tonight', 'This Saturday'): "
    ).strip()

    if not date_query:
        print("Date cannot be empty.")
        return

    # Build a context string from our curated directory to ground the model's tracking strategy
    sources_context = ", ".join([s["name"] for s in directory])

    prompt = (
        f"You are a local Twin Cities concierge analyzer. Find and list public events happening on the date: '{date_query}'.\n"
        f"Prioritize monitoring key venues and frameworks mentioned here: {sources_context}.\n"
        f"Provide a clean list including: Event Name, Venue/Location, Time, and brief details. "
        f"Format the output elegantly using markdown bullet points. Clear, accurate sorting only."
    )

    print(f"\nQuerying live data streams via Gemini for '{date_query}'...")

    try:
        # Utilizing gemini-2.5-flash with Google Search enabled for live temporal lookups
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}], temperature=0.2
            ),
        )
        print(f"\n=== Events Scheduled for {date_query} ===")
        print(response.text)
        print("=========================================")
    except Exception as e:
        print(f"An error occurred while gathering event data: {e}")


def main():
    client = get_gemini_client()
    directory = DEFAULT_DIRECTORY.copy()

    while True:
        print("\n=========================================")
        print("    Twin Cities Event Portal Console     ")
        print("=========================================")
        print("1. View & Update Calendar Source List")
        print("2. Search Events on a Specific Date")
        print("3. Exit")

        main_choice = input("Select an option (1-3): ").strip()

        if main_choice == "1":
            manage_directory(directory)
        elif main_choice == "2":
            search_events_by_date(client, directory)
        elif main_choice == "3":
            print("Exiting application. Have a great day in the Twin Cities!")
            break
        else:
            print("Invalid choice. Enter 1, 2, or 3.")


if __name__ == "__main__":
    main()
