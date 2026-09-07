import requests
import pandas as pd
import re

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime


# ---------------------------------------------------------
# Basic setup
# ---------------------------------------------------------

BASE_URL = "https://analyst-assessment-production.up.railway.app"

headers = {
    "User-Agent": "Mozilla/5.0"
}


# ---------------------------------------------------------
# Get HTML from a page
# ---------------------------------------------------------

def get_soup(url):
    response = requests.get(
        url,
        headers=headers,
        timeout=15
    )

    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser"
    )


# ---------------------------------------------------------
# Find all community page links
# ---------------------------------------------------------

def get_community_links():

    start_urls = [
        BASE_URL,
        f"{BASE_URL}/communities"
    ]

    community_links = set()
    visited = set()
    queue = start_urls.copy()

    while queue:

        url = queue.pop(0)

        if url in visited:
            continue

        try:

            response = requests.get(
                url,
                headers=headers,
                timeout=15
            )

            response.raise_for_status()

            visited.add(url)

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            for a in soup.find_all(
                "a",
                href=True
            ):

                href = a["href"]

                full_url = urljoin(
                    BASE_URL,
                    href
                )

                # Capture individual community pages
                if "/communities/" in full_url:

                    community_links.add(
                        full_url
                    )

                # Follow community directory
                # and pagination pages
                if (
                    full_url.startswith(
                        f"{BASE_URL}/communities"
                    )
                    and full_url not in visited
                    and full_url not in queue
                ):

                    queue.append(
                        full_url
                    )

        except Exception as e:

            print(
                "Error:",
                url,
                e
            )

    return sorted(
        community_links
    )


# ---------------------------------------------------------
# Extract information from one community page
# ---------------------------------------------------------

def scrape_community(url):

    soup = get_soup(url)


    # -----------------------------------------------------
    # Community name
    # -----------------------------------------------------

    heading = soup.find("h1")

    name = (
        heading.get_text(
            " ",
            strip=True
        )
        if heading
        else None
    )


    # -----------------------------------------------------
    # Address
    # -----------------------------------------------------

    address = None
    street = None
    city = None
    state = None
    zip_code = None

    # Find the text "Address"
    address_label = soup.find(
        string=re.compile(
            r"^\s*Address\s*$",
            re.IGNORECASE
        )
    )

    if address_label:

        # Usually the address is
        # stored in the next <dd>
        address_element = (
            address_label.find_next("dd")
        )

        if address_element:

            # Get each address line separately
            address_lines = list(
                address_element.stripped_strings
            )

            if len(address_lines) >= 2:

                street = address_lines[0]

                city_state_zip = (
                    address_lines[1]
                )

                match = re.match(
                    r"(.+?),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$",
                    city_state_zip
                )

                if match:

                    city = (
                        match.group(1).strip()
                    )

                    state = (
                        match.group(2).strip()
                    )

                    zip_code = (
                        match.group(3).strip()
                    )

                else:

                    # Keep the full address
                    # if parsing fails
                    address = " ".join(
                        address_lines
                    )

            elif len(address_lines) == 1:

                address = address_lines[0]


    # -----------------------------------------------------
    # Care offerings
    # -----------------------------------------------------

    care_offerings = []

    care_label = soup.find(
        string=re.compile(
            r"^\s*Care Offerings\s*$",
            re.IGNORECASE
        )
    )

    if care_label:

        # Look at the elements after
        # the care offerings label
        parent = care_label.parent

        # Find the next <dd>
        care_element = (
            parent.find_next("dd")
        )

        if care_element:

            care_offerings = [
                item.strip()
                for item in care_element.stripped_strings
                if item.strip()
            ]


    # -----------------------------------------------------
    # Fallback for care offerings
    # -----------------------------------------------------

    if not care_offerings:

        text = soup.get_text(
            " ",
            strip=True
        )

        match = re.search(
            r"Care Offerings\s+(.+?)\s+Administrator",
            text,
            re.IGNORECASE
        )

        if match:

            care_text = (
                match.group(1).strip()
            )

            # Known Bellhaven care types
            known_care_types = [
                "Assisted Living",
                "Memory Support",
                "Short-Term Rehabilitation & Nursing"
            ]

            for care_type in known_care_types:

                if (
                    care_type.lower()
                    in care_text.lower()
                ):

                    care_offerings.append(
                        care_type
                    )


    # -----------------------------------------------------
    # Build final address if needed
    # -----------------------------------------------------

    if not address:

        address_parts = []

        if street:
            address_parts.append(street)

        if city:
            address_parts.append(city)

        if state:
            address_parts.append(state)

        if zip_code:
            address_parts.append(zip_code)

        address = " ".join(
            address_parts
        )


    # -----------------------------------------------------
    # Return one clean record
    # -----------------------------------------------------

    return {

        "name": name,

        "street": street,

        "city": city,

        "state": state,

        "zip_code": zip_code,

        "care_offerings": "; ".join(
            care_offerings
        ),

        "source_url": url,

        "scraped_at": datetime.now().isoformat()

    }


# ---------------------------------------------------------
# Get all community links
# ---------------------------------------------------------

community_links = get_community_links()

print()
print("=" * 50)
print(
    "Community pages found:",
    len(community_links)
)
print("=" * 50)


# ---------------------------------------------------------
# Scrape every community
# ---------------------------------------------------------

records = []

for i, url in enumerate(
    community_links,
    start=1
):

    try:

        print(
            f"[{i}/{len(community_links)}] "
            f"Scraping {url}"
        )

        record = scrape_community(
            url
        )

        records.append(
            record
        )

    except Exception as e:

        print(
            f"ERROR scraping {url}: {e}"
        )


# ---------------------------------------------------------
# Create dataframe
# ---------------------------------------------------------

df = pd.DataFrame(
    records
)


# ---------------------------------------------------------
# Remove exact duplicates
# ---------------------------------------------------------

df = df.drop_duplicates(
    subset=["source_url"]
)


# ---------------------------------------------------------
# Display final results
# ---------------------------------------------------------

print()
print("=" * 50)
print("FINAL RESULTS")
print("=" * 50)

print(
    "Locations scraped:",
    len(df)
)

print()

print(
    df.to_string(
        index=False
    )
)


# ---------------------------------------------------------
# Save results
# ---------------------------------------------------------

df.to_csv(
    "website_locations.csv",
    index=False
)

print()
print(
    "Saved to: website_locations.csv"
)