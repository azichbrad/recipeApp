import requests
from bs4 import BeautifulSoup
import json
import re
from fractions import Fraction

def convert_to_metric(line, ingredient_name):
    densities = {'flour': 120, 'sugar': 200, 'butter': 227, 'rice': 185, 'oats': 90, 'milk': 240, 'water': 240, 'honey': 340, 'oil': 218}
    pattern = r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)\s*(cup|oz|ounce|lb|pound|tbsp|tablespoon|tsp|teaspoon)s?"
    match = re.search(pattern, line.lower())
    if match:
        qty_str = match.group(1); unit = match.group(2)
        try:
            if " " in qty_str and "/" in qty_str: whole, frac = qty_str.split(); val = float(whole) + float(Fraction(frac))
            else: val = float(Fraction(qty_str))
        except: return line
        
        new_val = 0; new_unit = ""; ingredient_density = 240 
        for key, density in densities.items():
            if key in ingredient_name.lower(): ingredient_density = density; break
        
        if 'cup' in unit: new_val = val * ingredient_density; new_unit = "g"
        elif 'oz' in unit or 'ounce' in unit: new_val = val * 28.35; new_unit = "g"
        elif 'lb' in unit or 'pound' in unit: new_val = val * 453.59; new_unit = "g"
        elif 'tbsp' in unit or 'tablespoon' in unit: new_val = val * 15; new_unit = "ml"
        elif 'tsp' in unit or 'teaspoon' in unit: new_val = val * 5; new_unit = "ml"
        return f"{int(new_val)}{new_unit} {line[match.end():]}"
    return line

def scale_line(line, multiplier, to_metric=False):
    if multiplier == 1 and not to_metric: return line
    pattern = r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)"
    match = re.match(pattern, line.strip())
    if match:
        number_str = match.group(1); original_text = line.strip()[len(number_str):]
        try:
            if " " in number_str and "/" in number_str: whole, frac = number_str.split(); val = float(whole) + float(Fraction(frac))
            else: val = float(Fraction(number_str))
            val = val * multiplier
            if to_metric: return convert_to_metric(f"{val} {original_text.strip()}", original_text)
            if val.is_integer(): new_num_str = str(int(val))
            else: new_num_str = str(round(val, 2))
            return f"{new_num_str}{original_text}"
        except: return line 
    return line

def get_recipe_data(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        recipe_data = None
        
        # Plan A: JSON-LD
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and '@graph' in data: data = data['@graph']
                if not isinstance(data, list): data = [data]
                for item in data:
                    if 'Recipe' in item.get('@type', []): recipe_data = item; break
            except: continue
            if recipe_data: break
        if recipe_data: return recipe_data

        # Fallbacks (Plan B & C)
        fallback_data = {"name": "Unknown Recipe", "image": None, "recipeIngredient": [], "recipeInstructions": []}
        if soup.find("h1"): fallback_data["name"] = soup.find("h1").get_text().strip()
        og_image = soup.find("meta", property="og:image")
        if og_image: fallback_data["image"] = og_image["content"]
        
        for list_tag in soup.find_all(['ul', 'ol']):
            if 'ingredient' in str(list_tag.get('class', '')).lower():
                for li in list_tag.find_all('li'): fallback_data["recipeIngredient"].append(li.get_text(" ", strip=True))
        if not fallback_data["recipeIngredient"]:
            for header in soup.find_all(['h2', 'h3', 'h4', 'h5']):
                if 'ingredient' in header.get_text().lower():
                    next_list = header.find_next(['ul', 'ol'])
                    if next_list:
                        for li in next_list.find_all('li'): fallback_data["recipeIngredient"].append(li.get_text(" ", strip=True))
        
        for list_tag in soup.find_all(['ul', 'ol', 'div']):
            if any(x in str(list_tag.get('class', '')).lower() for x in ['instruction', 'step']):
                 if list_tag.name in ['ul', 'ol']:
                     for li in list_tag.find_all('li'): fallback_data["recipeInstructions"].append(li.get_text(" ", strip=True))
        
        if fallback_data["recipeIngredient"]: return fallback_data
        return None
    except Exception as e: return f"Error: {e}"