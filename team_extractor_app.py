import streamlit as st
import re
from PIL import Image
import pytesseract

# 1️⃣ Tesseract path for Streamlit Cloud (required for OCR)
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# 2️⃣ App title
st.title("Team Sheet Extractor")

# 3️⃣ Input for team name
team_name = st.text_input("Enter Team Name (this will be added to all players):")

# 4️⃣ Checkbox to include player numbers
show_numbers = st.checkbox("Include player numbers?", value=True)

# 5️⃣ Text area for pasting team sheet data
data_input = st.text_area("Paste team sheet data here:")

# 6️⃣ Option to upload image
uploaded_file = st.file_uploader("Or upload a photo of a team sheet", type=["png", "jpg", "jpeg"])

# 7️⃣ Initialize list for lines to process
lines = []

# 8️⃣ Extract text if an image is uploaded
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    extracted_text = pytesseract.image_to_string(image)
    lines = extracted_text.split("\n")
elif data_input:
    lines = data_input.split("\n")

# 9️⃣ Process each line to extract just numbers + names
extracted_players = []

for line in lines:
    # Regex explanation:
    # ^\s*        : start of line, optional whitespace
    # (\d+)?      : optional number (captured if present)
    # \s*         : optional space
    # [\w\-'.]+   : first part of name (letters, dash, apostrophe, period)
    # (?:\s[\w\-'.]+)+ : one or more additional name parts (e.g., middle or last names)
    match = re.search(r"^\s*(\d+)?\s*[\w\-'.]+(?:\s[\w\-'.]+)+", line)
    if match:
        player_text = match.group(0).strip()
        if team_name:
            player_text += f" of the {team_name}"
        extracted_players.append(player_text)

# 1️⃣0️⃣ Display the cleaned team sheet
st.subheader("Extracted Team Sheet")
st.text("\n".join(extracted_players))

# 1️⃣1️⃣ Download button for CSV
if extracted_players:
    csv_text = "\n".join(extracted_players)
    st.download_button(
        label="Download as CSV",
        data=csv_text,
        file_name=f"{team_name}_team.csv",
        mime="text/csv"
    )

