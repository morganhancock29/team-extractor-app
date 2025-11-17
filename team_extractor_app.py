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

# --- List of countries / terms to ignore ---
countries = [
    "Australia", "United States", "New Zealand", "Netherlands", "South Sudan",
    "India", "England", "Canada", "South Africa", "Sri Lanka", "Bangladesh",
    "West Indies", "Ireland", "Scotland", "Zimbabwe", "Afghanistan", "Kenya",
    "Namibia", "UAE", "Oman", "Nepal", "Hong Kong", "Singapore", "Malaysia",
    "Thailand", "Japan", "China", "Fiji", "Germany", "Italy", "France", "Brazil",
    "Argentina", "Belgium", "Denmark", "Sweden", "Norway", "Finland", "Russia",
    "Poland", "Mexico", "USA", "America", "AUS", "Aus", "NZ"
]

# Sort countries by length descending to remove multi-word countries first
countries.sort(key=lambda x: len(x.split()), reverse=True)

# --- Processing ---
extracted_players = []

if input_text:
    lines = input_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove any * before or after number
        line_clean = re.sub(r"^\*?\s*(\d+)\s*\*?\s*", r"\1 ", line)

        # Extract optional number at the start
        num_match = re.match(r"^(\d+)", line_clean)
        number = num_match.group(1) if num_match else ""

        # Remove the number for name detection
        line_no_number = re.sub(r"^\d+\s*", "", line_clean)

        # Remove all country names
        for country in countries:
            line_no_number = re.sub(rf"\b{re.escape(country)}\b", "", line_no_number, flags=re.IGNORECASE)

        line_no_number = line_no_number.strip()
        if not line_no_number:
            continue

        # Capture first 2-3 capitalized words as player name
        name_match = re.findall(r"[A-Z][a-zA-Z'`.-]+(?:\s[A-Z][a-zA-Z'`.-]+){0,2}", line_no_number)
        if name_match:
            name = name_match[0]

            # Append team text if provided
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
