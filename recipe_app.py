import streamlit as st
from utils.db import supabase_auth, supabase_db
from utils.scraper import get_recipe_data, scale_line

# --- Page Config ---
st.set_page_config(
    page_title="Chef Mode", 
    page_icon="👨‍🍳",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Load CSS ---
with open('assets/style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# --- Sidebar Logic ---
if 'user' not in st.session_state: st.session_state.user = None

with st.sidebar:
    st.markdown("<h1 style='text-align: center; margin-bottom: 20px;'>👨‍🍳 Chef Mode</h1>", unsafe_allow_html=True)
    
    if not st.session_state.user:
        tab1, tab2 = st.tabs(["Log In", "Sign Up"])
        with tab1:
            with st.form("login_form"):
                st.text_input("Email", key="login_email")
                st.text_input("Password", type="password", key="login_pass")
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("Log In", type="primary"):
                    result = supabase_auth("login", st.session_state.login_email, st.session_state.login_pass)
                    if "error" in result: st.error("Login failed.")
                    else:
                        st.session_state.user = result.get("user", {}).get("email") or result.get("email")
                        st.rerun()
        with tab2:
            st.caption("Create a free account to save recipes.")
            with st.form("signup_form"):
                st.text_input("Email", key="su_email")
                st.text_input("Password", type="password", key="su_pass")
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("Sign Up"):
                    if len(st.session_state.su_pass) < 6: st.error("Password too short.")
                    else:
                        result = supabase_auth("signup", st.session_state.su_email, st.session_state.su_pass)
                        if "error" in result: st.error(result['error'])
                        else:
                            st.session_state.user = st.session_state.su_email
                            st.rerun()
    else:
        st.success(f"Signed in as: {st.session_state.user}")
        if st.button("Log Out"):
            st.session_state.user = None
            st.session_state.recipe_data = None
            st.rerun()
        
        st.divider()
        st.subheader("📖 My Cookbook")
        saved_recipes = supabase_db("GET", "recipes", params={"select": "*", "user_email": f"eq.{st.session_state.user}"})
        if saved_recipes:
            for saved in saved_recipes:
                if st.button(saved['recipe_name'], key=saved['id']):
                    st.session_state.recipe_data = saved['recipe_data']
                    st.rerun()
        else:
            st.info("No recipes saved yet.")

# --- Main Interface ---
if 'recipe_data' not in st.session_state: st.session_state.recipe_data = None

st.title("🍳 Chef Mode")
st.write("Turn any recipe URL into a clean, ad-free cooking view.")

query_params = st.query_params
link_url = query_params.get("url", "")
url = st.text_input("Paste Recipe URL:", value=link_url)

trigger_fetch = st.button("Clean Recipe", type="primary") or (link_url and url == link_url and st.session_state.recipe_data is None)

if trigger_fetch and url:
    with st.spinner("Chef is scraping..."):
        data = get_recipe_data(url)
        st.session_state.recipe_data = data

if st.session_state.recipe_data:
    recipe = st.session_state.recipe_data
    if isinstance(recipe, dict):
        st.divider()
        col_title, col_save = st.columns([3, 1])
        with col_title: st.subheader(recipe.get('name', 'Unknown Recipe'))
        with col_save:
            if st.session_state.user:
                if st.button("❤️ Save", use_container_width=True):
                    payload = {"user_email": st.session_state.user, "recipe_name": recipe.get('name', 'Unknown'), "recipe_data": recipe, "url": url}
                    if supabase_db("POST", "recipes", json_data=payload):
                        st.toast("Saved!", icon="✅"); st.rerun()
            else:
                st.button("Login to Save", disabled=True, use_container_width=True)

        image = recipe.get('image')
        if image:
            img_url = image[0] if isinstance(image, list) else (image.get('url') if isinstance(image, dict) else image)
            st.image(img_url, use_container_width=True)

        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1: multiplier = st.radio("Portions", [0.5, 1.0, 2.0], index=1, horizontal=True, format_func=lambda x: f"{x}x", label_visibility="collapsed")
            with c2: metric_mode = st.toggle("Metric Units", value=False)

        tab_ing, tab_inst = st.tabs(["🛒 Ingredients", "🔪 Instructions"])
        with tab_ing:
            for ingredient in recipe.get('recipeIngredient', []):
                st.markdown(f"- {scale_line(ingredient, multiplier, metric_mode)}")
        with tab_inst:
            clean_steps = []
            raw_steps = recipe.get('recipeInstructions', [])
            if isinstance(raw_steps, list):
                for step in raw_steps:
                    if isinstance(step, str): clean_steps.append(step)
                    elif isinstance(step, dict): clean_steps.append(step.get('text', ''))
                    elif isinstance(step, list): 
                        for s in step: clean_steps.append(s.get('text', '') if isinstance(s, dict) else s)
            for i, step in enumerate(clean_steps, 1):
                st.markdown(f"**{i}.** {step}")

    elif isinstance(recipe, str) and "Error" in recipe: st.error(recipe)
    else: st.error("Could not find recipe data.")