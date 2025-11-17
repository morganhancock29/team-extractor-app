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

# Words to ignore entirely after name
ignore_words = [
    "All-rounders", "Wicketkeepers", "Bowlers",
    "Forwards", "Defenders", "Goalkeepers", "Midfielders",
    "Forward", "Defender", "Goalkeeper", "Midfielder",
    # Basketball positions
    "Point Guard", "PG", "Shooting Guard", "SG", "Small Forward", "SF",
    "Power Forward", "PF", "Center", "C"
]

# Optional countries to ignore if they appear after name
ignore_countries = [
    "Australia", "AUS", "Aus", "New Zealand", "NZ",
    "United States", "America", "USA", "Canada",
    "England", "South Africa", "India", "Pakistan", "Sri Lanka", "West Indies",
    "Bangladesh", "Afghanistan", "Ireland", "Scotland", "Netherlands", "Germany", "France",
    "Italy", "Spain", "Portugal", "Belgium", "Greece", "Turkey", "China", "Japan", "Korea",
    "Brazil", "Argentina", "Mexico", "Sweden", "Norway", "Denmark", "Finland", "Poland",
    "Russia", "Ukraine", "Egypt", "Morocco", "Nigeria"
]

if input_text:
    lines = input_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Skip headings
        if any(line.lower().startswith(h.lower()) for h in ignore_words):
            continue

        # Remove leading "*" and spaces
        line = re.sub(r"^[\*\s]+", "", line)

        # Extract leading number if present
        num_match = re.match(r"^(\d+)", line)
        number = num_match.group(1) if num_match else ""

        # Remove number for regex matching
        line_no_number = re.sub(r"^\d+\s*", "", line)

        # Remove anything in parentheses
        line_no_parens = re.sub(r"\s*[\(\[].*?[\)\]]", "", line_no_number)

        # Regex to match 2+ capitalized words at the start (the player's name)
        name_match = re.match(r"^([A-Z][a-zA-Z'`.-]+(?:\s[A-Z][a-zA-Z'`.-]+)+)", line_no_parens)
        if name_match:
            name = name_match.group(1)

            # Append team text
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
