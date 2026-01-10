import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import re
from fractions import Fraction

# --- Page Configuration ---
st.set_page_config(page_title="Recipe Cleaner", page_icon="🍳")

st.title("🍳 Recipe Cleaner")

# --- 1. DEEP LINK LOGIC ---
query_params = st.query_params
link_url = query_params.get("url", "")
url = st.text_input("Recipe URL:", value=link_url)

# --- HELPER: Fraction Converter ---
def scale_line(line, multiplier):
    if multiplier == 1:
        return line
    
    # Regex to find numbers/fractions at the START of the line
    # Matches: "1 1/2", "1/2", "1.5", "2"
    pattern = r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)"
    match = re.match(pattern, line.strip())
    
    if match:
        number_str = match.group(1)
        original_text = line.strip()[len(number_str):] # The rest of the string (" cups of flour")
        
        try:
            # Handle mixed fractions like "1 1/2"
            if " " in number_str and "/" in number_str:
                whole, frac = number_str.split()
                val = float(whole) + float(Fraction(frac))
            else:
                val = float(Fraction(number_str))
            
            # Scale it
            new_val = val * multiplier
            
            # Format nicely (remove .0 if it's a whole number)
            if new_val.is_integer():
                new_num_str = str(int(new_val))
            else:
                new_num_str = str(round(new_val, 2))
                
            return f"{new_num_str}{original_text}"
        except:
            return line # If math fails, return original
            
    return line

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

        # --- PLAN A: JSON-LD ---
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

        if recipe_data: return recipe_data

        # --- PLAN B: HTML FALLBACK ---
        fallback_data = {
            "name": "Unknown Recipe",
            "image": None,
            "recipeIngredient": [],
            "recipeInstructions": []
        }

        # Title
        og_title = soup.find("meta", property="og:title")
        if og_title: fallback_data["name"] = og_title["content"]
        elif soup.find("h1"): fallback_data["name"] = soup.find("h1").get_text().strip()

        # Image
        og_image = soup.find("meta", property="og:image")
        if og_image: fallback_data["image"] = og_image["content"]

        # Ingredients
        for list_tag in soup.find_all(['ul', 'ol']):
            if 'ingredient' in str(list_tag.get('class', '')).lower():
                for li in list_tag.find_all('li'):
                    text = li.get_text(" ", strip=True)
                    if text: fallback_data["recipeIngredient"].append(text)
        
        # Instructions
        for list_tag in soup.find_all(['ul', 'ol', 'div']):
            class_name = str(list_tag.get('class', '')).lower()
            if any(x in class_name for x in ['instruction', 'direction', 'step', 'method']):
                if list_tag.name in ['ul', 'ol']:
                    for li in list_tag.find_all('li'):
                        text = li.get_text(" ", strip=True)
                        if text: fallback_data["recipeInstructions"].append(text)
                else:
                    for p in list_tag.find_all(['p', 'div']):
                        text = p.get_text(" ", strip=True)
                        if len(text) > 10: fallback_data["recipeInstructions"].append(text)

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
                img_url = ""
                if isinstance(image, list): img_url = image[0]
                elif isinstance(image, dict): img_url = image.get('url')
                elif isinstance(image, str): img_url = image
                
                if img_url:
                    st.image(img_url, use_container_width=True)

            # 3. Ingredients with SCALER
            st.subheader("Ingredients")
            
            # --- PORTION SCALER UI ---
            scale_col, _ = st.columns([2, 1])
            multiplier = scale_col.radio(
                "Scale Portion:", 
                [0.5, 1.0, 2.0], 
                index=1, 
                horizontal=True,
                format_func=lambda x: f"{x}x"
            )
            
            ingredients = recipe.get('recipeIngredient', [])
            
            if not ingredients:
                st.warning("Could not automatically find ingredients on this site.")
            
            for ingredient in ingredients:
                scaled_text = scale_line(ingredient, multiplier)
                st.checkbox(scaled_text) 

            # 4. Instructions
            st.subheader("Instructions")
            instructions = recipe.get('recipeInstructions', [])
            
            if not instructions:
                st.warning("Could not automatically find instructions on this site.")

            clean_steps = []
            for step in instructions:
                if isinstance(step, str):
                    clean_steps.append(step)
                elif isinstance(step, dict): 
                    clean_steps.append(step.get('text', ''))
                elif isinstance(step, list): 
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
