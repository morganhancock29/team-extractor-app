import streamlit as st
import pandas as pd
import re
from io import StringIO
from PIL import Image
import pytesseract

# Configure pytesseract for Streamlit Cloud
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

st.set_page_config(page_title="Team Sheet Cleaner", layout="wide")

st.title("Team Sheet Cleaner")

# Input options
input_type = st.radio("Select input type:", ["Paste Text", "Upload Image"])

raw_text = ""

if input_type == "Paste Text":
    raw_text = st.text_area("Paste your team sheet here:")

elif input_type == "Upload Image":
    uploaded_file = st.file_uploader("Upload an image", type=["png","jpg","jpeg"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        raw_text = pytesseract.image_to_string(image)

# Team name input
team_name_input = st.text_input("Enter the text you want to appear after each player:")

# Numbers toggle
show_numbers = st.checkbox("Include player numbers", value=True)

def extract_players(text):
    """
    Extracts player numbers and names only.
    Ignores any country, dates, stats, etc.
    """
    players = []
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove starting asterisks
        line = re.sub(r'^\*+\s*', '', line)

        # Match number at start, followed by name (letters, spaces, hyphens, apostrophes)
        match = re.match(r'(\d+)\s+([A-Za-zÀ-ÖØ-öø-ÿ \-\'\.]+)', line)
        if match:
            number = match.group(1)
            name = match.group(2).strip()
            players.append({"Number": number, "Name": name})
        else:
            # Try matching lines with only name and no number
            match_name_only = re.match(r'([A-Za-zÀ-ÖØ-öø-ÿ \-\'\.]+)', line)
            if match_name_only:
                name = match_name_only.group(1).strip()
                players.append({"Number": "", "Name": name})
    return players

if raw_text:
    extracted = extract_players(raw_text)
    
    if extracted:
        # Add team name if provided
        for player in extracted:
            player["Team"] = f"{team_name_input}" if team_name_input else ""
        
        # Prepare DataFrame
        df = pd.DataFrame(extracted)
        
        # Show result
        st.subheader("Extracted Team Sheet")
        st.dataframe(df)

        # CSV Export
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download CSV",
            data=csv_buffer.getvalue(),
            file_name="team_sheet.csv",
            mime="text/csv"
        )
    else:
        st.warning("No players found in the input. Please check the formatting.")
