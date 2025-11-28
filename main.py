import streamlit as st
import os
from pathlib import Path
from src.ui.utils.get_directories import get_subdirectories

BASE_DIR = "inputs/data"

# ---- Fonction qui liste les sous-dossiers ----
def list_subdirs():
    return get_subdirectories(BASE_DIR)

# ---- Fonction qui change le keyword ----
def update_keyword():
    st.session_state.filtered_subdirs = [
        d for d in st.session_state.subdirs
        if st.session_state.keyword.lower() in d.lower()
    ]
    # Met à jour l'index par défaut
    if st.session_state.filtered_subdirs:
        st.session_state.default_index = st.session_state.subdirs.index(
            st.session_state.filtered_subdirs[0]
        )
    else:
        st.session_state.default_index = 0


# ---- SESSION STATE INITIALISATION ----
if "subdirs" not in st.session_state:
    st.session_state.subdirs = list_subdirs()

if "keyword" not in st.session_state:
    st.session_state.keyword = ""

if "filtered_subdirs" not in st.session_state:
    st.session_state.filtered_subdirs = []

if "default_index" not in st.session_state:
    st.session_state.default_index = 0


# ---- DIALOG ----

@st.dialog(title="Create New Simulation")
def simulation_dialog(): 
    # Selectbox 1 : keyword
    # st.selectbox(
    #     "Mot-clé",
    #     ["GBIS", "RBDF", "Scope R1"],
    #     key="keyword",
    #     on_change=update_keyword
    # )

    keywordx = st.selectbox(
        "Filtrer les sous-répertoires par mot-clé",
        options = ['GBIS', 'RBDF', 'Scope R1', ''],
        key="keywordx"
    )
    dirs = st.session_state.subdirs
    if keywordx:
        dirs_select = [
            d for d in st.session_state.subdirs
            if keywordx.lower() in d.lower()
        ]
        default_index = st.session_state.subdirs.index(dirs_select[0]) if dirs_select else 0
        st.session_state.default_index = default_index
    # Selectbox 2 : tous les sous-dossiers avec sélection auto
    st.selectbox(
        "Sous-répertoire",
        options=dirs,
        index=st.session_state.default_index,
        key="selected_subdir"
    )
if st.button("Create Simulation", type="primary"):
    
    simulation_dialog()

st.session_state.default_index

    
