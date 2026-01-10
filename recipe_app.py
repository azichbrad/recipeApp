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

# --- HELPER: Unit Converter ---
def convert_to_metric(line, ingredient_name):
    # Basic density map (g per cup)
    densities = {
        'flour': 120, 'sugar': 200, 'butter': 227, 'rice': 185, 
        'oats': 90, 'milk': 240, 'water': 240, 'honey': 340, 'oil': 218
    }
    
    # 1. Parse the quantity (fractions/decimals)
    pattern = r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)\s*(cup|oz|ounce|lb|pound|tbsp|tablespoon|tsp|teaspoon)s?"
    match = re.search(pattern, line.lower())
    
    if match:
        qty_str = match.group(1)
        unit = match.group(2)
        
        # Convert text number to float
        try:
            if " " in qty_str and "/" in qty_str:
                whole, frac = qty_str.split()
                val = float(whole) + float(Fraction(frac))
            else:
                val = float(Fraction(qty_str))
        except:
            return line

        # Conversions
        new_val = 0
        new_unit = ""
        
        # Handle specific ingredients (Volume -> Mass)
        ingredient_density = 240 # Default to water/milk weight if unknown
        for key, density in densities.items():
            if key in ingredient_name.lower():
                ingredient_density = density
                break

        if 'cup' in unit:
            new_val = val * ingredient_density
            new_unit = "g"
        elif 'oz' in unit or 'ounce' in unit:
            new_val = val * 28.35
            new_unit = "g"
        elif 'lb' in unit or 'pound' in unit:
            new_val = val * 453.59
            new_unit = "g"
        elif 'tbsp' in unit or 'tablespoon' in unit:
            new_val = val * 15
            new_unit = "ml"
        elif 'tsp' in unit or 'teaspoon' in unit:
            new_val = val * 5
            new_unit = "ml"
            
        # Format output
        return f"{int(new_val)}{new_unit} {line[match.end():]}"
        
    return line

# --- HELPER: Portion Scaler ---
def scale_line(line, multiplier, to_metric=False):
    if multiplier == 1 and not to_metric:
        return line
    
    # Regex to find numbers/fractions at the START of the line
    pattern = r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)"
    match = re.match(pattern, line.strip())
    
    if match:
        number_str = match.group(1)
        original_text = line.strip()[len(number_str):]
        
        try:
            # Parse number
            if " " in number_str and "/" in number_str:
                whole, frac = number_str.split()
                val = float(whole) + float(Fraction(frac))
            else:
                val = float(Fraction(number_str))
            
            # 1. Scale it first
            val = val * multiplier
            
            # 2. Convert to Metric if requested
            if to_metric:
                # Reconstruct line with new scaled value to pass to converter
                temp_line = f"{val} {original_text.strip()}"
                return convert_to_metric(temp_line, original_text)
            
            # Just Scaling (No Metric)
            if val.is_integer():
                new_num_str = str(int(val))
            else:
                new_num_str = str(round(val, 2))
                
            return f"{new_num_str}{original_text}"
        except:
            return line 
            
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

            # 3. Ingredients
            st.subheader("Ingredients")
            
            # --- UI CONTROLS ---
            col1, col2 = st.columns(2)
            with col1:
                multiplier = st.radio("Portions:", [0.5, 1.0, 2.0], index=1, horizontal=True, format_func=lambda x: f"{x}x")
            with col2:
                metric_mode = st.toggle("Use Metric (g/ml)", value=False)
            
            ingredients = recipe.get('recipeIngredient', [])
            
            if not ingredients:
                st.warning("Could not automatically find ingredients on this site.")
            
            for ingredient in ingredients:
                # Apply scaling AND metric conversion
                final_text = scale_line(ingredient, multiplier, metric_mode)
                st.checkbox(final_text) 

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
