import streamlit as st
import re
import io
import csv
from datetime import datetime

st.set_page_config(page_title="Team Sheet Extractor", layout="wide")
st.title("Team Sheet Extractor")

# --- Sidebar ---
st.sidebar.header("Options")
include_numbers = st.sidebar.checkbox("Include Numbers", value=True)  # Default ON
number_prefix = st.sidebar.text_input("Text to prepend before number", value="")  # New prefix box
team_text = st.sidebar.text_input("Text to append after player name", value="")
file_name_input = st.sidebar.text_input("Filename (optional)", value="")

# Download format dropdown
file_format = st.sidebar.selectbox("Download format", ["CSV (aText)", "TSV (PhotoMechanic)"])

# Checkbox to skip left column
skip_left_column = st.sidebar.checkbox("Skip left column of numbers", value=False)

# FAQ box
st.sidebar.markdown("---")
st.sidebar.markdown("""
### ❓ FAQ

**Why do some names not work?**  
Some unusual name formats might be skipped, including:  
- Very short names (<4 letters)  
- Single-word names shorter than 4 letters  
- Lines not starting with a letter  

Check the **Skipped Lines** section below.

**CSV vs TSV**  
- **CSV (aText)** is recommended for aText  
- **TSV (PhotoMechanic)** preserves spacing and special characters for PhotoMechanic

**Skip left column**  
If your sheet includes row numbers like:  
`1 26 Taylor Smith`  
turn ON this option to ignore the first number.

**Number Prefix**  
If you want to prepend a string before the number (e.g., `a1`, `b2`), type it in the box above.
""")

st.sidebar.markdown("---")
st.sidebar.markdown("Paste team sheet text below:")

# --- Input ---
input_text = st.text_area("Paste team sheet here", height=250)

# --- Processing ---
extracted_players = []
skipped_lines = []
potential_issues = []  # will hold tuples (original_line, reason)

ignore_words = [
    "All-rounders", "Wicketkeepers", "Bowlers",
    "Forwards", "Defenders", "Goalkeepers", "Midfielders",
    "Forward", "Defender", "Goalkeeper", "Midfielder",
    "Point Guard", "PG", "Shooting Guard", "SG", "Small Forward", "SF",
    "Power Forward", "PF", "Center", "C"
]

ignore_countries = [
    "Australia", "AUS", "New Zealand", "NZ", "United States", "America", "USA", "Canada",
    "England", "South Africa", "India", "Pakistan", "Sri Lanka", "West Indies",
    "Bangladesh", "Afghanistan", "Ireland", "Scotland", "Netherlands", "Germany", "France",
    "Italy", "Spain", "Portugal", "Belgium", "Greece", "Turkey", "China", "Japan", "Korea",
    "Brazil", "Argentina", "Mexico", "Sweden", "Norway", "Denmark", "Finland", "Poland",
    "Russia", "Ukraine", "Egypt", "Morocco", "Nigeria"
]

surname_prefixes = ["de", "van", "von", "da", "del", "di", "du", "la", "le", "Mac", "Mc", "van der", "van den", "der"]
prefix_pattern = r"(?:van der|van den|de|van|von|da|del|di|du|la|le|Mac|Mc|der)?"

if input_text:
    lines = input_text.splitlines()
    for line in lines:
        original_line = line.strip()
        if not original_line:
            continue

        # Skip headings
        if any(original_line.lower().startswith(h.lower()) for h in ignore_words):
            continue

        # Clean line
        line_clean = re.sub(r"^[\*\s]+", "", original_line)
        # Remove parenthetical country tags (but keep text around them)
        line_clean = re.sub(r"\(.*?\)", "", line_clean)
        for word in ignore_words + ignore_countries:
            line_clean = re.sub(rf"\b{re.escape(word)}\b", "", line_clean)

        # Extract number
        numbers_in_line = re.findall(r"\d+", line_clean)
        if skip_left_column:
            number = numbers_in_line[1] if len(numbers_in_line) > 1 else ""
            line_no_number = re.sub(r"^\d+\s+\d+\s*", "", line_clean).strip()
        else:
            number = numbers_in_line[0] if len(numbers_in_line) > 0 else ""
            line_no_number = re.sub(r"^\d+\s*", "", line_clean).strip()

        # Prepend number prefix if any
        if number and number_prefix:
            number = f"{number_prefix}{number}"

        line_no_number = re.sub(r"^(GK|DF|MF|FW)\b", "", line_no_number).strip()

        # Capitalize first word for parsing (only for matching)
        line_parsed = line_no_number
        if line_parsed and line_parsed[0].islower():
            line_parsed = line_parsed[0].upper() + line_parsed[1:]

        # Multi-word regex
        multi_name_regex = re.compile(
            rf"[A-Z][a-zA-Z'`.-]+(?:\s{prefix_pattern}\s?[A-Z][a-zA-Z'`.-]+)+"
        )
        # Single-word ≥4 letters
        single_name_regex = re.compile(r"\b[A-Z][a-zA-Z'`.-]{3,}\b")

        match = multi_name_regex.search(line_parsed)
        if match:
            name = match.group().strip()
            # If we captured only a single word (unexpected), set to single-word logic
            name_words = name.split()
        else:
            match_single = single_name_regex.search(line_parsed)
            name = match_single.group().strip() if match_single else None
            name_words = name.split() if name else []

        # If name was found but is single word while original has a lowercase last token,
        # flag that we only captured first name because last name lacked capital.
        if name and len(name_words) == 1:
            # Look at original_line tokens after removing leading numbers
            after_num = re.sub(r"^\s*\d+\s*", "", original_line).strip()
            tokens = after_num.split()
            if len(tokens) >= 2:
                # if second token is all-lowercase (or starts lowercase) assume that's why it was missed
                second = tokens[1]
                if second and second[0].islower():
                    reason = "Last name not capitalised — only first name captured"
                    potential_issues.append((original_line, reason))

        # If no name, create a helpful explanation
        if not name:
            reason = None
            # Remove leading number for inspection
            after_num = re.sub(r"^\s*\d+\s*", "", original_line).strip()
            tokens = after_num.split()

            # If first token starts lowercase -> first name not capitalised
            if tokens and tokens[0] and tokens[0][0].islower():
                reason = "First name not capitalised"
            # Else if there's a second token and it's lowercase -> last name not capitalised
            elif len(tokens) >= 2 and tokens[1] and tokens[1][0].islower():
                reason = "Last name not capitalised"
            # Else if single token and too short
            elif len(tokens) == 1 and len(tokens[0]) < 4:
                reason = "Single-word name too short"
            # Else if digits appear after the first token (dates mid-line) they may interfere
            elif re.search(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", original_line) or re.search(r"\b\d{2,4}\b", " ".join(tokens[1:])):
                reason = "Numbers or dates mid-line may have interfered"
            else:
                reason = "Unusual format — name could not be parsed"

            potential_issues.append((original_line, reason))
            skipped_lines.append(original_line)
        else:
            if team_text:
                name += f" {team_text}"
            extracted_players.append((number, name))

# --- Output ---
if extracted_players:
    st.subheader("Extracted Team Sheet")
    st.text("\n".join([f"{num}\t{name}" if include_numbers and num else name for num, name in extracted_players]))

    # -------------------------
    # POSSIBLE ERRORS SECTION
    # -------------------------
    if potential_issues:
        st.markdown("### ⚠️ Possible Errors Detected")
        explanations = [f"{line}  — {reason}" for line, reason in potential_issues]
        st.text("\n".join(explanations))
    # -------------------------

    if file_name_input.strip():
        base_filename = file_name_input.strip()
    else:
        base_filename = f"team_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    output = io.StringIO()
    if file_format == "TSV (PhotoMechanic)":
        filename = base_filename + ".tsv"
        delimiter = "\t"
        mime = "text/tab-separated-values"
    else:
        filename = base_filename + ".csv"
        delimiter = ","
        mime = "text/csv"

    writer = csv.writer(output, delimiter=delimiter, quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for num, name in extracted_players:
        if include_numbers:
            writer.writerow([num, name])
        else:
            writer.writerow(["", name])

    st.download_button(
        label=f"Download as {file_format}",
        data=output.getvalue(),
        file_name=filename,
        mime=mime
    )

    if skipped_lines:
        st.subheader("Skipped Lines (names not recognized)")
        st.text("\n".join(skipped_lines))
else:
    st.info("No player names detected. Make sure your team sheet is pasted correctly.")
