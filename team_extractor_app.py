# team_extractor_app.py

import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import easyocr
import io

# ---- Set up pytesseract path for Streamlit Cloud ----
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

st.set_page_config(page_title="Team Sheet Extractor", layout="wide")
st.title("Team Sheet Extractor")

# --- Sidebar options ---
st.sidebar.header("Options")
team_name = st.sidebar.text_input("Enter team name:", "")
show_numbers = st.sidebar.checkbox("Show numbers", value=True)

st.write("### Paste team sheet text or upload an image")

# --- Paste text area ---
text_input = st.text_area("Paste your team sheet here:")

# --- Image upload ---
uploaded_file = st.file_uploader("Or upload a team sheet image:", type=["png","jpg","jpeg","pdf"])

extracted_text = ""

# --- OCR for images ---
if uploaded_file:
    if uploaded_file.type == "application/pdf":
        st.warning("PDF upload not supported yet. Please convert to image.")
    else:
        image = Image.open(uploaded_file)
        # Using pytesseract for OCR
        extracted_text = pytesseract.image_to_string(image)

# Use pasted text if no image OCR
if text_input:
    extracted_text = text_input

# --- Process text ---
def extract_players(text):
    lines = text.split("\n")
    players = []
    for line in lines:
        line = line.strip()
        if line == "":
            continue
        # Split on whitespace, first part might be a number
        parts = line.split()
        if len(parts) == 0:
            continue
        # Check if first part is a number
        if parts[0].isdigit():
            number = parts[0]
            name = " ".join(parts[1:])
        else:
            number = ""
            name = " ".join(parts)
        players.append((number, name))
    return players

players_list = extract_players(extracted_text)

# --- Add team name ---
def format_players(players, team, show_numbers=True):
    formatted = []
    for number, name in players:
        if team != "":
            name += f" of the {team}"
        if show_numbers and number != "":
            formatted.append(f"{number} | {name}")
        else:
            formatted.append(f"{name}")
    return formatted

if players_list:
    formatted_list = format_players(players_list, team_name, show_numbers)
    st.write("### Extracted Team Sheet")
    st.text("\n".join(formatted_list))

    # --- Download CSV ---
    df = pd.DataFrame(formatted_list, columns=["Player"])
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"{team_name}_team.csv",
        mime="text/csv"
    )
else:
    st.info("Paste some text or upload an image to see the team sheet.")
