import streamlit as st
from pymongo import MongoClient
import os


# Get URI safely from Streamlit Secrets (for cloud) or environment variable (for local)
MONGO_URI = st.secrets.get("MONGO_URI", os.getenv("MONGO_URI"))
@st.cache_resource
def get_mongo_client():
    uri = MONGO_URI
    return MongoClient(
        uri,
        datetime_conversion="DATETIME_AUTO",
        socketTimeoutMS=600000,
        connectTimeoutMS=60000,
        maxIdleTimeMS=120000
    )

client = get_mongo_client()
db = client['healthstackv2']