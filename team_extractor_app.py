# team_extractor_app.py

import streamlit as st
import pandas as pd
import re
from io import StringIO
from PIL import Image
import pytesseract

# ---- APP HEADER ----
st.title("Team Sheet Extractor")
st.markdown("""
Paste a team sheet or upload an image, enter the team name once, and get a clean list of players.
""")

# ---- TEAM NAME INPUT ----
team_name = st.text_input("Team name to append:")

# ---- NUMBER TOGGLE ----
numbers_on = st.checkbox("Include player numbers", value=True)

# ---- INPUT OPTIONS ----
st.subheader("Input options")
input_option = st.radio("Select input type:", ("Paste text", "Upload image"))

player_text = ""
if input_option == "Paste text":
    player_text = st.text_area("Paste your team sheet here:")

elif input_option == "Upload image":
    uploaded_file = st.file_uploader("Upload team sheet image", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        player_text = pytesseract.image_to_string(image)
        st.text_area("Extracted text from image:", value=player_text, height=200)

# ---- EXTRACTION FUNCTION ----
def extract_players(text):
    players = []
    # Split lines and process each
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Match optional number at start
        match = re.match(r'^(\d+)\s*[\|]?\s*(.+)', line)
        if match:
            number = match.group(1)
            name = match.group(2)
        else:
            number = ""
            name = line
        # Clean name
        name = re.sub(r'\s{2,}', ' ', name)  # replace multiple spaces
        if numbers_on:
            players.append(f"{number} | {name} of the {team_name}" if team_name else f"{number} | {name}")
        else:
            players.append(f"{name} of the {team_name}" if team_name else name)
    return players

# ---- PROCESS BUTTON ----
if st.button("Extract Team"):
    if not player_text:
        st.warning("Please provide input text or upload an image!")
    else:
        player_list = extract_players(player_text)
        # Show results
        st.subheader("Extracted Players")
        st.text("\n".join(player_list))
        
        # Download as CSV
        df = pd.DataFrame(player_list, columns=["Player"])
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="team_sheet.csv",
            mime="text/csv"
        )
