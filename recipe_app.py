import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import re

# --- Page Configuration ---
st.set_page_config(page_title="Recipe Cleaner", page_icon="🍳")

st.title("🍳 Recipe Cleaner")

# --- 1. DEEP LINK LOGIC ---
query_params = st.query_params
link_url = query_params.get("url", "")
url = st.text_input("Recipe URL:", value=link_url)

# --- The Scraper Logic ---
def get_recipe_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        recipe_data = None

        # --- PLAN A: JSON-LD (Structured Data) ---
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and '@graph' in data:
                    data = data['@graph']
                if not isinstance(data, list):
                    data = [data]
                for item in data:
                    if 'Recipe' in item.get('@type', []):
                        recipe_data = item
                        break
            except:
                continue
            if recipe_data: break

        # If JSON-LD worked, return it immediately
        if recipe_data:
            return recipe_data

        # --- PLAN B: FALLBACK HTML SCRAPING ---
        # If we are here, JSON-LD failed. Let's look for HTML tags manually.
        fallback_data = {
            "name": "Unknown Recipe",
            "image": None,
            "recipeIngredient": [],
            "recipeInstructions": []
        }

        # 1. Try to find the Title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            fallback_data["name"] = og_title["content"]
        else:
            h1 = soup.find("h1")
            if h1: fallback_data["name"] = h1.get_text().strip()

        # 2. Try to find the Image
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            fallback_data["image"] = og_image["content"]

        # 3. Try to find Ingredients
        # We look for <ul> or <ol> that have "ingredient" in their class name
        for list_tag in soup.find_all(['ul', 'ol']):
            class_name = str(list_tag.get('class', '')).lower()
            if 'ingredient' in class_name:
                for li in list_tag.find_all('li'):
                    text = li.get_text(" ", strip=True)
                    if text: fallback_data["recipeIngredient"].append(text)
        
        # 4. Try to find Instructions
        # We look for lists with "instruction", "direction", or "step"
        for list_tag in soup.find_all(['ul', 'ol', 'div']):
            class_name = str(list_tag.get('class', '')).lower()
            if any(x in class_name for x in ['instruction', 'direction', 'step', 'method']):
                # If it's a list, grab list items
                if list_tag.name in ['ul', 'ol']:
                    for li in list_tag.find_all('li'):
                        text = li.get_text(" ", strip=True)
                        if text: fallback_data["recipeInstructions"].append(text)
                # If it's a div, looks for paragraphs or spans
                else:
                    for p in list_tag.find_all(['p', 'div']):
                        text = p.get_text(" ", strip=True)
                        if len(text) > 10: # Avoid empty spacers
                            fallback_data["recipeInstructions"].append(text)

        # Only return fallback data if we actually found something meaningful
        if fallback_data["recipeIngredient"] or fallback_data["recipeInstructions"]:
            return fallback_data
        
        return None

    except Exception as e:
        return f"Error: {e}"

# --- The Trigger ---
should_run = st.button("Get Recipe") or (link_url and url == link_url)

if should_run and url:
    with st.spinner("Scraping recipe..."):
        recipe = get_recipe_data(url)

        if isinstance(recipe, dict):
            # 1. Title
            st.header(recipe.get('name', 'Unknown Recipe'))

            # 2. Image
            image = recipe.get('image')
            if image:
                # Handle fallback string vs JSON-LD list/dict
                img_url = ""
                if isinstance(image, list): img_url = image[0]
                elif isinstance(image, dict): img_url = image.get('url')
                elif isinstance(image, str): img_url = image
                
                if img_url:
                    st.image(img_url, use_container_width=True)

            # 3. Ingredients
            st.subheader("Ingredients")
            ingredients = recipe.get('recipeIngredient', [])
            
            if not ingredients:
                st.warning("Could not automatically find ingredients on this site.")
            
            for ingredient in ingredients:
                st.checkbox(ingredient) 

            # 4. Instructions
            st.subheader("Instructions")
            instructions = recipe.get('recipeInstructions', [])
            
            if not instructions:
                st.warning("Could not automatically find instructions on this site.")

            # Clean steps helper
            clean_steps = []
            for step in instructions:
                if isinstance(step, str):
                    clean_steps.append(step)
                elif isinstance(step, dict): # JSON-LD complex object
                    clean_steps.append(step.get('text', ''))
                elif isinstance(step, list): # Sometimes nested lists
                    for substep in step:
                        if isinstance(substep, dict): clean_steps.append(substep.get('text', ''))
                        elif isinstance(substep, str): clean_steps.append(substep)

            for i, step in enumerate(clean_steps, 1):
                st.markdown(f"**{i}.** {step}")

        elif recipe is None:
            st.error("Could not find recipe data. This site is very old or uses a unique structure we can't parse.")
        else:
            st.error(recipe)

elif not url:
    st.write("Paste a URL or use the Share Sheet shortcut to start.")
