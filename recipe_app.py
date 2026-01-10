import streamlit as st
import requests
from bs4 import BeautifulSoup
import json

# --- Page Configuration ---
st.set_page_config(page_title="Recipe Cleaner", page_icon="🍳")

st.title("🍳 Recipe Cleaner")
st.write("Paste a URL below to strip away the ads and life stories.")

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
                # Normalize data (sometimes it's a list, sometimes a dict, sometimes a graph)
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

# --- The User Interface ---
url = st.text_input("Recipe URL:")

if st.button("Get Recipe"):
    if url:
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
                
                # Clean steps helper
                clean_steps = []
                for step in instructions:
                    if isinstance(step, str):
                        clean_steps.append(step)
                    elif isinstance(step, dict):
                        clean_steps.append(step.get('text', ''))

                for i, step in enumerate(clean_steps, 1):
                    st.markdown(f"**{i}.** {step}")

            elif recipe is None:
                st.error("Could not find recipe data on this page. It might be an older site without JSON-LD.")
            else:
                st.error(recipe)
    else:
        st.warning("Please paste a URL first.")