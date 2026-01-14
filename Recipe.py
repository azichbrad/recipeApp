import requests
from bs4 import BeautifulSoup
import json

def scrape_recipe(url):
    # 1. Fake a browser visit (User-Agent) so the site doesn't block us
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Check if the request was successful
        
        soup = BeautifulSoup(response.content, 'html.parser')

        # 2. Find the JSON-LD script tag
        json_scripts = soup.find_all('script', type='application/ld+json')
        
        recipe_data = None

        # 3. Loop through scripts to find the 'Recipe' type
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                
                # Handle cases where the JSON is a list of objects
                if isinstance(data, list):
                    for item in data:
                        if 'Recipe' in item.get('@type', []):
                            recipe_data = item
                            break
                # Handle cases where the JSON is a single object
                elif 'Recipe' in data.get('@type', []):
                    recipe_data = data
                # Handle cases where it's a graph (common in WordPress/Yoast)
                elif '@graph' in data:
                    for item in data['@graph']:
                        if 'Recipe' in item.get('@type', []):
                            recipe_data = item
                            break
                
                if recipe_data:
                    break
            except (json.JSONDecodeError, TypeError):
                continue

        if not recipe_data:
            return "Could not find structured recipe data on this page."

        # 4. Extract and Print the Data
        print(f"--- {recipe_data.get('name', 'Unknown Recipe')} ---\n")
        
        # Image
        image = recipe_data.get('image')
        if isinstance(image, list):
            print(f"[Image URL]: {image[0]}\n")
        elif isinstance(image, dict):
             print(f"[Image URL]: {image.get('url')}\n")
        else:
            print(f"[Image URL]: {image}\n")

        print("INGREDIENTS:")
        for ingredient in recipe_data.get('recipeIngredient', []):
            print(f"- {ingredient}")
            
        print("\nINSTRUCTIONS:")
        instructions = recipe_data.get('recipeInstructions', [])
        
        # Instructions can be a list of strings or a list of "HowToStep" objects
        for i, step in enumerate(instructions, 1):
            if isinstance(step, str):
                print(f"{i}. {step}")
            elif isinstance(step, dict):
                text = step.get('text', '')
                print(f"{i}. {text}")

    except Exception as e:
        return f"An error occurred: {e}"

# Example Usage:
# You can replace this URL with any recipe from a major site (AllRecipes, FoodNetwork, NYT, specific food blogs)
url = input("Paste recipe URL here: ")
scrape_recipe(url)