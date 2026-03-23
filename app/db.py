import os
import pandas as pd
import streamlit as st
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

@st.cache_resource
def get_driver():
    return GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", os.getenv("NEO4J_ROOT_PASSWORD"))
    )

def run_query(query: str, params: dict = None) -> pd.DataFrame:
    try:
        driver = get_driver()
        with driver.session() as session:
            result = session.run(query, params or {})
            records = [r.data() for r in result]
            if not records:
                return pd.DataFrame()
            df = pd.DataFrame(records)
            for col in df.columns:
                df[col] = df[col].apply(
                    lambda x: str(x) if not isinstance(x, (int, float, bool, type(None))) else x
                )
            return df
    except Exception as e:
        st.error(f"Error de conexión a Neo4j: {e}")
        return pd.DataFrame()
