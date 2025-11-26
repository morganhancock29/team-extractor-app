import streamlit as st
import re
import io
import csv
import unicodedata
from datetime import datetime
from collections import defaultdict

st.set_page_config(page_title="Team Sheet Extractor", layout="wide")
st.title("Team Sheet Extractor")

# --- Sidebar ---
st.sidebar.header("Options")
include_numbers = st.sidebar.checkbox("Include Numbers", value=True)  # Default ON
number_prefix = st.sidebar.text_input("Text to prepend before number", value="")  # prefix box
team_text = st.sidebar.text_input("Text to append after player name", value="")
file_name_input = st.sidebar.text_input("Filename (optional)", value="")

# Download format dropdown
file_format = st.sidebar.selectbox("Download format", ["CSV (aText)", "TSV (PhotoMechanic)"])

# Checkbox to skip left column of numbers (kept for backward compat)
skip_left_column = st.sidebar.checkbox("Skip left column of numbers", value=False)

# NEW: Show initials list (appends initials lines under the main list)
show_initials_list = st.sidebar.checkbox("Show initials list (append after main list)", value=False)

# FAQ box
st.sidebar.markdown("---")
st.sidebar.markdown("""
### ❓ FAQ

**Why do some names not work?**  
Some unusual name formats might be skipped, including:  
- Very short names (<4 letters)  
- Single-word names shorter than 4 letters  
- Lines not starting with a letter  

Check the **Skipped Lines** / **Possible Errors** section below.

**CSV vs TSV**  
- **CSV (aText)** is recommended for aText  
- **TSV (PhotoMechanic)** preserves spacing and special characters

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
input_text = st.text_area("Paste team sheet here", height=300)

# --- Helpers ---
def remove_accents(s: str) -> str:
    """Strip diacritics (é -> e)"""
    if not s:
        return s
    nfkd = unicodedata.normalize('NFKD', s)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def initial_by_n(name: str, n: int) -> str:
    """
    Build initials by taking first n letters of up to first two name parts (or one if single).
    Returned in lowercase, no separators.
    Examples:
      n=1 -> 'oa' (Óscar Arribas -> 'oa')
      n=2 -> 'osar' (Óscar Arribas -> 'osar')  -- actually will be 'osar' when parts are 'os' + 'ar'
    To match your instruction (first two letters of each name part), we concatenate in order.
    """
    parts = [p for p in name.split() if p]
    if not parts:
        return ""
    # Use up to first two parts (first name + last name)
    if len(parts) == 1:
        return parts[0][:n].lower()
    else:
        return (parts[0][:n] + parts[1][:n]).lower()

def base_initial(name: str) -> str:
    """Default initials: first letter of first and first letter of last (lowercase).
       If single-name, return first letter only."""
    parts = [p for p in name.split() if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0][0].lower()
    return (parts[0][0] + parts[1][0]).lower()

# List of common 3-letter country codes (unique)
COUNTRY_CODES = {
    "AFG","ALG","ARG","AUS","AUT","BEL","BRA","CAN","CHN","COL","CRO","CZE","DEN","EGY","ENG","ESP",
    "EST","ETH","FIN","FRA","GER","GHA","GRC","HUN","INA","IRL","IRN","ISR","ITA","JAM","JPN","KOR",
    "MAR","MEX","MLI","NED","NGA","NOR","NZL","PAN","PER","PHI","POL","POR","ROU","RUS","SAU","SCO",
    "SEN","SRB","SVK","SWE","SUI","TUN","TUR","UKR","URU","USA","VEN","WAL","ZAF","MAS","AZE","BOL",
    "BUL","CHI","CMR","CIV","CYP","DOM","ECU","ERI","GAB","GEO","GUI","HON","HKG","ISL","JOR","KEN",
    "KSA","KAZ","KWT","LAO","LAT","LTU","LUX","MAD","MNE","NAM","NCA","NEP","NIG","OMA","PAR","PLE",
    "QAT","RSA","RWA","SIN","SLO","SOM","SWZ","TJK","TKM","TLS","TOG","TPE","UAE","UGA","UZB","VIE",
    "ZAM","ZIM"
}

# Words to ignore for headings and positions
IGNORE_WORDS = [
    "All-rounders","Wicketkeepers","Bowlers","Forwards","Defenders","Goalkeepers","Midfielders",
    "Forward","Defender","Goalkeeper","Midfielder","Point Guard","PG","Shooting Guard","SG",
    "Small Forward","SF","Power Forward","PF","Center","C"
]

# surname prefix pattern used in name regex
surname_prefixes = ["de","van","von","da","del","di","du","la","le","Mac","Mc","van der","van den","der"]
prefix_pattern = r"(?:van der|van den|de|van|von|da|del|di|du|la|le|Mac|Mc|der)?"

# --- Main processing ---
extracted_players = []       # list of (number, name)
skipped_lines = []           # original lines not parsed to name
potential_issues = []        # (original_line, reason)

if input_text:
    lines = input_text.splitlines()
    for line in lines:
        original_line = line.rstrip("\n").strip()
        if not original_line:
            continue

        # skip heading lines (like "All-rounders")
        if any(original_line.lower().startswith(h.lower()) for h in IGNORE_WORDS):
            continue

        # normalize and clean parenthetical groups
        working = re.sub(r"^[\*\s]+", "", original_line)          # leading stars/spaces
        working = re.sub(r"\(.*?\)", "", working).strip()        # remove parenthetical blocks

        # remove known long ignore words/countries conservatively
        for w in IGNORE_WORDS:
            working = re.sub(rf"\b{re.escape(w)}\b", "", working, flags=re.IGNORECASE)
        # also remove words from ignore_countries if they appear as full words
        # small list to be conservative (kept short to avoid removing names)
        ignore_countries = ["Australia","AUS","New Zealand","NZ","United States","USA","England","Brazil","Argentina"]
        for w in ignore_countries:
            working = re.sub(rf"\b{re.escape(w)}\b", "", working, flags=re.IGNORECASE)

        # 1) extract numbers in the line (all numeric tokens)
        numbers_in_line = re.findall(r"\d+", working)

        # handle skip_left_column option (older behaviour)
        if skip_left_column:
            # if user expects an index then actual number
            number = numbers_in_line[1] if len(numbers_in_line) > 1 else (numbers_in_line[0] if numbers_in_line else "")
            # remove up to two leading numbers (index + number) from working string
            working = re.sub(r"^\d+\s+\d+\s*", "", working).strip()
        else:
            number = numbers_in_line[0] if len(numbers_in_line) > 0 else ""
            # remove first leading number token if present
            working = re.sub(r"^\d+\s*", "", working).strip()

        # Now remove common position codes if at start (GK DF MF FW etc.)
        working = re.sub(r"^(GK|DF|MF|FW)\b\s*", "", working)

        # Tokenize the remaining string to remove a country code that may sit between position and name
        tokens = working.split()
        # if first token is a 3-letter uppercase country code (or uppercase in general), drop it
        if tokens and tokens[0].upper() in COUNTRY_CODES:
            tokens.pop(0)
        # also if second token (after e.g. a stray tab/spaces) is country code, handle that case:
        # (e.g., "DF  ESP  Oscar Arribas" -> tokens[0] might be 'DF' which was removed earlier, but handle defensively)
        if len(tokens) >= 2 and tokens[1].upper() in COUNTRY_CODES:
            tokens.pop(1)

        # Rebuild working name string after removals
        working_name = " ".join(tokens).strip()

        # Normalize accents *before* matching names so regex finds ASCII-friendly text
        working_name_norm = remove_accents(working_name)

        # Capitalize first character to help regex (but we match regardless)
        if working_name_norm and working_name_norm[0].islower():
            working_name_norm = working_name_norm[0].upper() + working_name_norm[1:]

        # Name extraction regexes
        multi_name_regex = re.compile(
            rf"[A-Z][a-zA-Z'`.\-]+(?:\s(?:{prefix_pattern})\s?[A-Z][a-zA-Z'`.\-]+)+"
        )
        single_name_regex = re.compile(r"\b[A-Z][a-zA-Z'`.\-]{3,}\b")

        match = multi_name_regex.search(working_name_norm)
        if match:
            name = match.group().strip()
        else:
            match_single = single_name_regex.search(working_name_norm)
            name = match_single.group().strip() if match_single else None

        # If no name parsed, attempt a fallback: take the whole normalized working_name if it has letters
        if not name and working_name_norm and re.search(r"[A-Za-z]", working_name_norm):
            # last resort: use trimmed working_name_norm as name if it looks reasonable
            possible = working_name_norm.strip()
            # avoid just numbers or single-letter junk
            if len(possible) >= 2:
                name = possible

        # Prepare potential issue reasons if something's off
        if not name:
            # inspect original tokens after removing leading number
            after_num = re.sub(r"^\s*\d+\s*", "", original_line).strip()
            tks = after_num.split()
            reason = None
            if tks and tks[0] and tks[0][0].islower():
                reason = "First name not capitalised"
            elif len(tks) >= 2 and tks[1] and tks[1][0].islower():
                reason = "Last name not capitalised"
            elif len(tks) == 1 and len(tks[0]) < 4:
                reason = "Single-word name too short"
            elif re.search(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", original_line) or re.search(r"\b\d{2,4}\b", " ".join(tks[1:])):
                reason = "Numbers or dates mid-line may have interfered"
            else:
                reason = "Unusual format — name could not be parsed"

            potential_issues.append((original_line, reason))
            skipped_lines.append(original_line)
            continue

        # finally, restore accents in output if you want original accents removed or kept:
        # currently we output the normalized (de-accented) name so regex works reliably
        # Option: if you prefer to output original accented name when available, we can map back.
        # For now keep de-accented name for consistency with matching:
        name_output = name  # already de-accented via working_name_norm

        # Append team text if provided
        if team_text:
            name_output = f"{name_output} {team_text}"

        # Apply number prefix if provided and number exists
        num_out = number
        if num_out and number_prefix:
            num_out = f"{number_prefix}{num_out}"

        extracted_players.append((num_out, name_output))

# --- Output / Initials logic ---
if extracted_players:
    st.subheader("Extracted Team Sheet")

    # Build main list lines (strings)
    main_lines = []
    for num, name in extracted_players:
        if include_numbers and num:
            main_lines.append(f"{num}\t{name}")
        else:
            main_lines.append(name)

    # If initials list requested, compute initials and resolve duplicates
    if show_initials_list:
        # Build initial structures
        initials_list = []  # parallel to extracted_players
        for num, name in extracted_players:
            initials_list.append(base_initial(name))

        # Map initials -> list of indices
        idx_map = defaultdict(list)
        for i, init in enumerate(initials_list):
            idx_map[init].append(i)

        # Resolve duplicates by expanding only conflicting groups
        # We'll attempt expansion n=2 then n=3 (per your instruction)
        for n in [2, 3]:
            # build new initials for only conflict groups, evaluate whether conflicts remain
            changed_any = False
            new_map = {}
            # compute new initials but only for indices that are currently in conflict groups
            new_initials = initials_list[:]  # copy
            for init, indices in list(idx_map.items()):
                if len(indices) > 1:
                    # expand for each index
                    for idx in indices:
                        name = extracted_players[idx][1]
                        expanded = initial_by_n(name, n)
                        new_initials[idx] = expanded
                    changed_any = True

            if not changed_any:
                # no conflicts present, nothing to do
                break

            # rebuild map and check if duplicates remain
            idx_map = defaultdict(list)
            for i, init in enumerate(new_initials):
                idx_map[init].append(i)

            # if no key has more than one index, we've resolved all duplicates
            if all(len(v) == 1 for v in idx_map.values()):
                initials_list = new_initials
                break
            else:
                # keep new_initials but continue to next expansion if n < 3
                initials_list = new_initials
                # continue loop to try next n

        # After resolution, append initials lines directly after main_lines (no header)
        initials_lines = []
        for init, (num, name) in zip(initials_list, extracted_players):
            # Format: "oa\tOscar Arribas"
            initials_lines.append(f"{init}\t{name}")

        # Compose combined output: main_lines followed immediately by initials_lines
        combined_lines = main_lines + initials_lines
        st.text("\n".join(combined_lines))
    else:
        # No initials requested: just show main list
        st.text("\n".join(main_lines))

    # -------------------------
    # POSSIBLE ERRORS SECTION
    # -------------------------
    if potential_issues:
        st.markdown("### ⚠️ Possible Errors Detected")
        explanations = [f"{line}  —  {reason}" for line, reason in potential_issues]
        st.text("\n".join(explanations))
    # -------------------------

    # --- File export (unchanged: initials not included in downloads) ---
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
