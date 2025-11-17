import streamlit as st
import pytesseract
from PIL import Image
import re
import io
import csv

# OCR setup
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

st.set_page_config(page_title="Team Sheet Extractor", layout="wide")
st.title("Team Sheet Extractor")

# --- Sidebar ---
st.sidebar.header("Options")
show_numbers = st.sidebar.checkbox("Include Numbers", value=True)
team_text = st.sidebar.text_input("Text to append after player name", value="")

st.sidebar.markdown("---")
st.sidebar.markdown("Paste team sheet text or upload an image below:")

# --- Input ---
input_text = st.text_area("Paste team sheet here", height=250)
uploaded_file = st.file_uploader("Or upload an image", type=["png", "jpg", "jpeg"])

# --- Extract text from image if uploaded ---
if uploaded_file:
    image = Image.open(uploaded_file)
    input_text += "\n" + pytesseract.image_to_string(image)

# --- Country list to ignore ---
countries = [
    "Australia", "United States", "New Zealand", "Netherlands", "South Sudan", 
    "India", "England", "Canada", "South Africa", "Sri Lanka", "Bangladesh", 
    "West Indies", "Ireland", "Scotland", "Zimbabwe", "Afghanistan", "Kenya", 
    "Namibia", "UAE", "Oman", "Nepal", "Hong Kong", "Singapore", "Malaysia", 
    "Thailand", "Japan", "China", "Fiji", "Germany", "Italy", "France", "Brazil", 
    "Argentina", "Belgium", "Denmark", "Sweden", "Norway", "Finland", "Russia", 
    "Poland", "Mexico", "USA", "Tanzania", "America", "AUS", "Aus", "NZ"
]

# --- Processing ---
extracted_players = []

if input_text:
    lines = input_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove starting "*" or other symbols
        line = re.sub(r"^[\*\s]+", "", line)

        # Remove leading numbers or country names
        tokens = line.split()
        while tokens and (tokens[0].isdigit() or tokens[0] in countries):
            tokens.pop(0)

        # Skip empty lines after removal
        if not tokens:
            continue

        # Optional: capture number at the very start (before popping)
        num_match = re.match(r"^(\d+)", line)
        number = num_match.group(1) if num_match else ""

        # Grab 2-3 capitalized words for name
        name_tokens = []
        for tok in tokens:
            if tok[0].isupper():
                name_tokens.append(tok)
                if len(name_tokens) == 3:
                    break
            else:
                break

        if name_tokens:
            name = " ".join(name_tokens)
            if team_text:
                name += f" {team_text}"

            if show_numbers and number:
                extracted_players.append(f"{number} | {name}")
            else:
                extracted_players.append(name)

# --- Output ---
if extracted_players:
    st.subheader("Extracted Team Sheet")
    st.text("\n".join(extracted_players))

    # CSV download
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
