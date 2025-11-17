import streamlit as st
import re
from PIL import Image
import pytesseract

# Tesseract path for Streamlit Cloud
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

st.title("Clean Team Sheet Extractor")

# Toggle for numbers
show_numbers = st.checkbox("Include player numbers?", value=True)

# Text area for pasting data
data_input = st.text_area("Paste team sheet data here:")

# Option to upload image
uploaded_file = st.file_uploader("Or upload a photo of a team sheet", type=["png", "jpg", "jpeg"])

lines = []

# OCR if image uploaded
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    extracted_text = pytesseract.image_to_string(image)
    lines = extracted_text.split("\n")
elif data_input:
    lines = data_input.split("\n")

extracted_players = []

# Regex to detect player number (optional) + name
player_pattern = re.compile(r"^\s*(\d+)?\s*([A-Z][\w\-'.]+(?:\s[A-Z][\w\-'.]+)+)")

# Keywords to skip
skip_keywords = ["all-rounders", "wicketkeepers", "bowlers", "batsmen", "team", "captain"]

for line in lines:
    line = line.strip()
    if not line:
        continue
    if any(skip in line.lower() for skip in skip_keywords):
        continue

    match = player_pattern.match(line)
    if match:
        number = match.group(1)
        name = match.group(2)

        if show_numbers and number:
            player_text = f"{number} | {name}"
        else:
            player_text = name

        extracted_players.append(player_text)

# Display results
st.subheader("Extracted Team Sheet")
st.text("\n".join(extracted_players))

# Download as CSV
if extracted_players:
    csv_text = "\n".join(extracted_players)
    st.download_button(
        label="Download as CSV",
        data=csv_text,
        file_name="team.csv",
        mime="text/csv"
    )


