import re
import sys


def validate_description(content):
    errors = []
    warnings = []

    # 1. Length Check
    char_count = len(content)
    if char_count > 5000:
        warnings.append(f"Description is very long ({char_count} chars). Be aware of platform-specific limits.")
    elif char_count < 100:
        warnings.append(f"Description is very short ({char_count} chars). Consider adding more detail.")

    # 2. Timestamp Check
    timestamp_pattern = r"\b\d{1,2}:\d{2}\b"
    timestamps = re.findall(timestamp_pattern, content)
    if not timestamps:
        warnings.append("No timestamps found. Timestamps help viewers navigate your video.")

    # 3. Link Check
    link_pattern = r"https?://\S+"
    links = re.findall(link_pattern, content)
    if not links:
        warnings.append("No links found. Consider adding calls to action or resource links.")

    # 4. Hashtag Check
    hashtag_pattern = r"#\w+"
    hashtags = re.findall(hashtag_pattern, content)
    if not hashtags:
        warnings.append("No hashtags found. Hashtags can improve searchability (exactly 5 recommended).")
    elif len(hashtags) > 5:
        errors.append(f"Too many hashtags: {len(hashtags)}. Please limit to exactly 5 most relevant ones.")
    elif len(hashtags) < 5:
        errors.append(f"Fewer than 5 hashtags found ({len(hashtags)}). Please provide exactly 5 as per SKILL.md.")

    # 5. Point of View Check (Heuristic)
    we_patterns = r"\b(we|our|ours|us)\b"
    if re.search(we_patterns, content, re.IGNORECASE):
        warnings.append("Detected 'we/our/us'. User preference is for first-person singular 'I/my'.")
    if not content.startswith("#"):
        warnings.append("Description does not start with a title (#). A clear title helps indexing.")

    return errors, warnings

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        with open(file_path, encoding="utf-8") as f:
            description_content = f.read()
    except FileNotFoundError:
        sys.exit(1)
    except OSError:
        sys.exit(1)

    errs, warns = validate_description(description_content)

    if warns:
        for _warn in warns:
            pass

    if errs:
        for _err in errs:
            pass
        sys.exit(1)

