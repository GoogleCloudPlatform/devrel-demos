"""GCP Region locations mapping dictionary."""

GCP_REGION_LOCATIONS: dict[str, dict[str, str]] = {
    # --- Americas ---
    "us-central1": {
        "city": "Council Bluffs, Iowa",
        "country": "United States",
        "flag": "🇺🇸",
    },
    "us-east1": {
        "city": "Moncks Corner, South Carolina",
        "country": "United States",
        "flag": "🇺🇸",
    },
    "us-east4": {
        "city": "Ashburn, Virginia",
        "country": "United States",
        "flag": "🇺🇸",
    },
    "us-east5": {
        "city": "Columbus, Ohio",
        "country": "United States",
        "flag": "🇺🇸",
    },
    "us-south1": {
        "city": "Dallas, Texas",
        "country": "United States",
        "flag": "🇺🇸",
    },
    "us-west1": {
        "city": "The Dalles, Oregon",
        "country": "United States",
        "flag": "🇺🇸",
    },
    "us-west2": {
        "city": "Los Angeles, California",
        "country": "United States",
        "flag": "🇺🇸",
    },
    "us-west3": {
        "city": "Salt Lake City, Utah",
        "country": "United States",
        "flag": "🇺🇸",
    },
    "us-west4": {
        "city": "Las Vegas, Nevada",
        "country": "United States",
        "flag": "🇺🇸",
    },
    "northamerica-northeast1": {
        "city": "Montréal, Quebec",
        "country": "Canada",
        "flag": "🇨🇦",
    },
    "northamerica-northeast2": {
        "city": "Toronto, Ontario",
        "country": "Canada",
        "flag": "🇨🇦",
    },
    "northamerica-south1": {
        "city": "Querétaro",
        "country": "Mexico",
        "flag": "🇲🇽",
    },
    "southamerica-east1": {
        "city": "Osasco, São Paulo",
        "country": "Brazil",
        "flag": "🇧🇷",
    },
    "southamerica-west1": {
        "city": "Santiago",
        "country": "Chile",
        "flag": "🇨🇱",
    },
    # --- Europe ---
    "europe-central2": {
        "city": "Warsaw",
        "country": "Poland",
        "flag": "🇵🇱",
    },
    "europe-north1": {
        "city": "Hamina",
        "country": "Finland",
        "flag": "🇫🇮",
    },
    "europe-north2": {
        "city": "Oslo",
        "country": "Norway",
        "flag": "🇳🇴",
    },
    "europe-southwest1": {
        "city": "Madrid",
        "country": "Spain",
        "flag": "🇪🇸",
    },
    "europe-west1": {
        "city": "St. Ghislain",
        "country": "Belgium",
        "flag": "🇧🇪",
    },
    "europe-west2": {
        "city": "London",
        "country": "United Kingdom",
        "flag": "🇬🇧",
    },
    "europe-west3": {
        "city": "Frankfurt",
        "country": "Germany",
        "flag": "🇩🇪",
    },
    "europe-west4": {
        "city": "Eemshaven",
        "country": "Netherlands",
        "flag": "🇳🇱",
    },
    "europe-west6": {
        "city": "Zurich",
        "country": "Switzerland",
        "flag": "🇨🇭",
    },
    "europe-west8": {
        "city": "Milan",
        "country": "Italy",
        "flag": "🇮🇹",
    },
    "europe-west9": {
        "city": "Paris",
        "country": "France",
        "flag": "🇫🇷",
    },
    "europe-west10": {
        "city": "Berlin",
        "country": "Germany",
        "flag": "🇩🇪",
    },
    "europe-west12": {
        "city": "Turin",
        "country": "Italy",
        "flag": "🇮🇹",
    },
    # --- Asia Pacific ---
    "asia-east1": {
        "city": "Changhua County",
        "country": "Taiwan",
        "flag": "🇹🇼",
    },
    "asia-east2": {
        "city": "Cyberport",
        "country": "Hong Kong",
        "flag": "🇭🇰",
    },
    "asia-northeast1": {
        "city": "Tokyo",
        "country": "Japan",
        "flag": "🇯🇵",
    },
    "asia-northeast2": {
        "city": "Osaka",
        "country": "Japan",
        "flag": "🇯🇵",
    },
    "asia-northeast3": {
        "city": "Seoul",
        "country": "South Korea",
        "flag": "🇰🇷",
    },
    "asia-south1": {
        "city": "Mumbai",
        "country": "India",
        "flag": "🇮🇳",
    },
    "asia-south2": {
        "city": "Delhi",
        "country": "India",
        "flag": "🇮🇳",
    },
    "asia-southeast1": {
        "city": "Jurong West",
        "country": "Singapore",
        "flag": "🇸🇬",
    },
    "asia-southeast2": {
        "city": "Jakarta",
        "country": "Indonesia",
        "flag": "🇮🇩",
    },
    "asia-southeast3": {
        "city": "Davao City",
        "country": "Philippines",
        "flag": "🇵🇭",
    },
    "australia-southeast1": {
        "city": "Sydney",
        "country": "Australia",
        "flag": "🇦🇺",
    },
    "australia-southeast2": {
        "city": "Melbourne",
        "country": "Australia",
        "flag": "🇦🇺",
    },
    # --- Middle East & Africa ---
    "africa-south1": {
        "city": "Johannesburg",
        "country": "South Africa",
        "flag": "🇿🇦",
    },
    "me-central1": {
        "city": "Doha",
        "country": "Qatar",
        "flag": "🇶🇦",
    },
    "me-central2": {
        "city": "Dammam",
        "country": "Saudi Arabia",
        "flag": "🇸🇦",
    },
    "me-west1": {
        "city": "Tel Aviv",
        "country": "Israel",
        "flag": "🇮🇱",
    },
}


def get_location_info(region_code: str) -> dict[str, str]:
    """Retrieve location details (city, country, flag) for a GCP region code."""
    return GCP_REGION_LOCATIONS.get(
        region_code,
        {
            "city": "Unknown",
            "country": "Unknown",
            "flag": "🌐",
        },
    )
