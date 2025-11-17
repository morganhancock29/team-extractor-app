import streamlit as st
import pandas as pd
from io import StringIO
import re
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

def extract_players_tabbed(text):
    """
    Extract only number + name from tab/space separated input.
    Ignores everything else.
    """
    players = []
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Split by tabs first
        parts = re.split(r'\t+', line)
        if len(parts) >= 2:
            number = parts[0].strip()
            name = parts[1].strip()

            # Remove any starting asterisks
            number = number.lstrip('*').strip()
            name = name.lstrip('*').strip()

            if not show_numbers:
                number = ""

            players.append({
                "Number": number,
                "Name": name,
                "Team": team_name_input
            })
    return players

if raw_text:
    extracted = extract_players_tabbed(raw_text)

    if extracted:
        df = pd.DataFrame(extracted)
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
