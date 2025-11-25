import streamlit as st
import re
import io
import csv
from datetime import datetime
import unicodedata

st.set_page_config(page_title="Team Sheet Extractor", layout="wide")
st.title("Team Sheet Extractor")

# --- Sidebar ---
st.sidebar.header("Options")
include_numbers = st.sidebar.checkbox("Include Numbers", value=True)
number_prefix = st.sidebar.text_input("Text to prepend before number", value="")
team_text = st.sidebar.text_input("Text to append after player name", value="")
file_name_input = st.sidebar.text_input("Filename (optional)", value="")

# Download format dropdown
file_format = st.sidebar.selectbox("Download format", ["CSV (aText)", "TSV (PhotoMechanic)"])

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
potential_issues = []

ignore_words = [
    "All-rounders", "Wicketkeepers", "Bowlers",
    "Forwards", "Defenders", "Goalkeepers", "Midfielders",
    "Forward", "Defender", "Goalkeeper", "Midfielder",
    "Point Guard", "PG", "Shooting Guard", "SG", "Small Forward", "SF",
    "Power Forward", "PF", "Center", "C"
]

# Top 100 FIFA country codes (3 letters)
country_codes = [
    "AFG","ALG","ARG","AUS","AUT","BEL","BRA","CAN","CHN","COL",
    "CRO","CZE","DEN","EGY","ENG","ESP","EST","ETH","FIN",
    "FRA","GER","GHA","GRC","HUN","INA","IRL","IRN","ISR","ITA",
    "JAM","JPN","KOR","MAR","MEX","MLI","NED","NGA","NOR","NZL",
    "PAN","PER","PHI","POL","POR","ROU","RUS","SAU","SCO","SEN",
    "SRB","SVK","SWE","SUI","TUN","TUR","UKR","URU","USA","VEN",
    "WAL","ZAF","MAS","AZE","MEX","JPN","GER","FRA","ENG","ESP"
]

surname_prefixes = ["de", "van", "von", "da", "del", "di", "du", "la", "le", "Mac", "Mc", "van der", "van den", "der"]
prefix_pattern = r"(?:van der|van den|de|van|von|da|del|di|du|la|le|Mac|Mc|der)?"

def remove_accents(input_str):
    return ''.join(c for c in unicodedata.normalize('NFD', input_str)
                   if unicodedata.category(c) != 'Mn')

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
        line_clean = re.sub(r"\(.*?\)", "", line_clean)

        # Remove ignore words
        for word in ignore_words:
            line_clean = re.sub(rf"\b{re.escape(word)}\b", "", line_clean)

        # Split tokens
        tokens = line_clean.split()
        # Remove leading numbers
        tokens = [t for t in tokens if not re.fullmatch(r"\d+", t)]
        # Remove position codes
        tokens = [t for t in tokens if t not in ["GK","DF","MF","FW"]]
        # Remove 3-letter country codes
        tokens = [t for t in tokens if t.upper() not in country_codes]

        # Reconstruct line
        line_no_number = " ".join(tokens)
        # Capitalize first character for parsing
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
            name_words = name.split()
        else:
            match_single = single_name_regex.search(line_parsed)
            name = match_single.group().strip() if match_single else None
            name_words = name.split() if name else []

        # Strip accents
        if name:
            name = remove_accents(name)

        # Handle issues
        if name and len(name_words) == 1:
            original_tokens = line_no_number.split()
            if len(original_tokens) >= 2:
                second = original_tokens[1]
                if second and second[0].islower():
                    reason = "Last name not capitalised — only first name captured"
                    potential_issues.append((original_line, reason))

        if not name:
            reason = "Name could not be parsed"
            potential_issues.append((original_line, reason))
            skipped_lines.append(original_line)
        else:
            # Add number prefix if any
            number = tokens[0] if tokens else ""
            if number_prefix and number:
                number = f"{number_prefix}{number}"
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
