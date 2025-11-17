import streamlit as st
import pytesseract
from PIL import Image
import re
import io
import csv

# Make sure pytesseract points to the right path on Streamlit Cloud
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

st.set_page_config(page_title="Team Sheet Extractor", layout="wide")
st.title("Team Sheet Extractor")

# --- Sidebar options ---
st.sidebar.header("Options")
show_numbers = st.sidebar.checkbox("Include Numbers", value=True)
team_text = st.sidebar.text_input("Text to add after player name", value="")

st.sidebar.markdown("---")
st.sidebar.markdown("Paste team sheet text below or upload an image to extract names.")

# --- Input section ---
input_text = st.text_area("Paste team sheet here", height=250)
uploaded_file = st.file_uploader("Or upload an image", type=["png", "jpg", "jpeg"])

extracted_players = []

# --- OCR extraction if image uploaded ---
if uploaded_file:
    image = Image.open(uploaded_file)
    text_from_image = pytesseract.image_to_string(image)
    input_text += "\n" + text_from_image

# --- Process input text ---
if input_text:
    lines = input_text.splitlines()
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        
        # Regex: number (optional) + player name
        # This will match:
        # "23 Jake Fraser-McGurk ..." or "Jake Fraser-McGurk ..."
        match = re.match(r"^\s*(\d+)?\s*[\|]?\s*([A-Z][A-Za-z'`.\-]+\s[A-Za-z'`.\-]+(?:\s[A-Za-z'`.\-]+)?)", line.strip())
        if match:
            number = match.group(1)
            name = match.group(2)
            
            # Append custom team text
            if team_text:
                name += f" {team_text}"
            
            if show_numbers and number:
                extracted_players.append(f"{number} | {name}")
            else:
                extracted_players.append(f"{name}")

# --- Output ---
if extracted_players:
    st.subheader("Extracted Team Sheet")
    st.text("\n".join(extracted_players))
    
    # --- Download as CSV ---
    output = io.StringIO()
    writer = csv.writer(output)
    for player in extracted_players:
        if show_numbers and '|' in player:
            number, name = map(str.strip, player.split('|', 1))
        else:
            number = ''
            name = player
        writer.writerow([number, name])
    csv_data = output.getvalue()
    
    st.download_button(
        label="Download as CSV",
        data=csv_data,
        file_name="team.csv",
        mime="text/csv"
    )
else:
    st.info("No player names detected. Make sure your team sheet is pasted correctly or image is clear.")
