import re

KNOWN_ENVIRONMENTS = ["CW 1.0", "CW 2.0", "Affinities 1.0", "UAT", "Production"]
KNOWN_SYSTEMS = ["Salesforce", "Checkout", "Wallet", "Client Portal", "MyCW", "Okta", "Talkdesk", "EPIC"]

def extract_known(value_list, text):
    for v in value_list:
        if v.lower() in text.lower():
            return v
    return "Unknown"

def parse_notes(notes: str):
    if not notes or len(notes.strip()) == 0:
        return "Unknown", "Unknown", "No details available"

    # Environment
    env_match = re.search(r"Environment[:\-]?\s*([^\n]+)", notes, re.IGNORECASE)
    if env_match:
        environment = env_match.group(1).strip()
    else:
        environment = extract_known(KNOWN_ENVIRONMENTS, notes)

    # System Impacted
    sys_match = re.search(r"System Impacted[:\-]?\s*([^\n]+)", notes, re.IGNORECASE)
    if sys_match:
        system_impacted = sys_match.group(1).strip()
    else:
        system_impacted = extract_known(KNOWN_SYSTEMS, notes)

    # Clean details
    details = re.sub(r"(https?://\S+)|(@[^\s]+)|(\*[^*]+\*)", "", notes)  # Remove URLs, mentions, bold markers
    details = re.sub(r"\s+", " ", details).strip()

    return environment, system_impacted, details

if __name__ == "__main__":
    # Test the parser with various scenarios
    test_cases = [
        "Environment: Production\nSystem Impacted: Salesforce\nCustomer reported unable to save changes @user.name https://example.com",
        "bug: Agent Portal attachments- unable to upload excel files; only pdf format successfully uploads to Opportunity",
        "Environment - CW 2.0 Issue with Checkout process *urgent*",
        "Production Salesforce issue with client portal login"
    ]
    
    for i, notes in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Input: {notes}")
        env, system, details = parse_notes(notes)
        print(f"Environment: {env}")
        print(f"System Impacted: {system}")
        print(f"Details: {details}")