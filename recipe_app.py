import streamlit as st
import requests
from bs4 import BeautifulSoup
import json

# --- Page Configuration ---
st.set_page_config(page_title="Recipe Cleaner", page_icon="🍳")

st.title("🍳 Recipe Cleaner")

# --- 1. DEEP LINK LOGIC ---
# Check if a URL was passed in the browser link (e.g. ?url=...)
query_params = st.query_params
link_url = query_params.get("url", "")

# If we found a link in the params, use it. Otherwise, leave blank.
url = st.text_input("Recipe URL:", value=link_url)

# --- The Scraper Logic ---
def get_recipe_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find JSON-LD
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
                        return item
            except:
                continue
        return None
    except Exception as e:
        return f"Error: {e}"

# --- The Trigger ---
# Run if the button is clicked OR if a link was passed automatically
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
                img_url = image[0] if isinstance(image, list) else (image.get('url') if isinstance(image, dict) else image)
                st.image(img_url, use_container_width=True)

            # 3. Ingredients
            st.subheader("Ingredients")
            ingredients = recipe.get('recipeIngredient', [])
            for ingredient in ingredients:
                st.checkbox(ingredient) 

            # 4. Instructions
            st.subheader("Instructions")
            instructions = recipe.get('recipeInstructions', [])
            
            clean_steps = []
            for step in instructions:
                if isinstance(step, str):
                    clean_steps.append(step)
                elif isinstance(step, dict):
                    clean_steps.append(step.get('text', ''))

            for i, step in enumerate(clean_steps, 1):
                st.markdown(f"**{i}.** {step}")

        elif recipe is None:
            st.error("Could not find recipe data. This site might not use standard JSON-LD.")
        else:
            st.error(recipe)

elif not url:
    st.write("Paste a URL or use the Share Sheet shortcut to start.")
