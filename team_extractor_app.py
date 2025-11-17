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

# --- Processing ---
extracted_players = []

# Words to ignore (countries, positions, etc.)
ignore_words = [
    "All-rounders", "Wicketkeepers", "Bowlers",
    "Forward", "Defender", "Goalkeeper", "Midfielder",
    "Guard", "Center", "Centre", "F", "G", "C",
    "Australia", "AUS", "Aus", "New Zealand", "NZ",
    "United States", "America", "USA", "United Kingdom",
    "England", "France", "Germany", "Italy", "Spain",
    "Portugal", "Netherlands", "Brazil", "Argentina",
    "China", "Japan", "South Korea", "South Africa",
    "India", "Pakistan", "Bangladesh", "Sri Lanka",
    "West Indies", "Ireland", "Scotland", "Belgium",
    "Sweden", "Norway", "Finland", "Denmark", "Poland",
    "Russia", "Ukraine", "Mexico", "Canada"
]

if input_text:
    lines = input_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove starting "*" or whitespace
        line = re.sub(r"^[\*\s]+", "", line)

        # Skip entire line if it matches any ignore words
        if any(word.lower() in line.lower() for word in ignore_words):
            continue

        # Optional number at start
        num_match = re.match(r"^(\d+)", line)
        number = num_match.group(1) if num_match else ""

        # Remove number for name detection
        line_no_number = re.sub(r"^\d+\s*", "", line)

        # Regex: find sequences of 2+ capitalised words (First Last)
        name_words = re.findall(r"[A-Z][a-zA-Z'`.-]+", line_no_number)
        if name_words:
            # Remove words completely inside parentheses/brackets
            name_words = [w for w in name_words if not re.match(r"^[\(\[].*?[\)\]]$", w)]
            name = " ".join(name_words)

            # Append custom team text
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
