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

        # Skip ignored headings
        if any(line.lower().startswith(h.lower()) for h in ignore_words):
            continue

        # Remove starting "*" or other symbols
        line = re.sub(r"^\*?\s*", "", line)

        # Look for optional number at start
        num_match = re.match(r"^(\d+)", line)
        number = num_match.group(1) if num_match else ""

        # Remove the number for name detection
        line_no_number = re.sub(r"^\d+\s*", "", line)

        # Remove anything in parentheses or brackets
        line_no_paren = re.sub(r"\s*[\(\[].*?[\)\]]", "", line_no_number)

        # Split line into words and collect name until an ignore word, country, lowercase word, or stat is reached
        words = line_no_paren.split()
        name_words = []
        for word in words:
            if word in ignore_words or word in ignore_countries:
                break
            if re.match(r"^[a-z]", word):
                break
            name_words.append(word)

        if name_words:
            name = " ".join(name_words)

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
