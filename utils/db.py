import streamlit as st
import requests

def get_config():
    try:
        return st.secrets["supabase"]["url"], st.secrets["supabase"]["key"]
    except:
        return None, None

def supabase_auth(action, email, password):
    url, key = get_config()
    if not url: return {"error": "Missing secrets"}
    
    headers = {"apikey": key, "Content-Type": "application/json"}
    payload = {"email": email, "password": password}
    
    if action == "signup": 
        endpoint = f"{url}/auth/v1/signup"
    else: 
        endpoint = f"{url}/auth/v1/token?grant_type=password"
        
    try:
        response = requests.post(endpoint, headers=headers, json=payload)
        if response.status_code != 200: return {"error": response.text}
        return response.json()
    except Exception as e: return {"error": str(e)}

def supabase_db(method, endpoint, params=None, json_data=None):
    url, key = get_config()
    if not url: return None
    
    api_url = f"{url}/rest/v1/{endpoint}"
    headers = {
        "apikey": key, 
        "Authorization": f"Bearer {key}", 
        "Content-Type": "application/json", 
        "Prefer": "return=representation"
    }
    
    try:
        if method == "GET": 
            response = requests.get(api_url, headers=headers, params=params)
        elif method == "POST": 
            response = requests.post(api_url, headers=headers, json=json_data)
        
        if response.status_code >= 400: return None
        return response.json()
    except: return None