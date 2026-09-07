import re
from difflib import SequenceMatcher

import pandas as pd


def normalize_text(value):
    """
    Standardize text before comparing website and CRM values.
    """

    if pd.isna(value):
        return ""

    value = str(value).lower().strip()

    # Remove the .0 added when ZIP codes were read as numbers
    if re.fullmatch(r"\d{5}\.0", value):
        value = value[:-2]

    replacements = {
        " street ": " st ",
        " avenue ": " ave ",
        " road ": " rd ",
        " boulevard ": " blvd ",
        " drive ": " dr ",
        " lane ": " ln ",
        " court ": " ct ",
        " highway ": " hwy ",
        " north ": " n ",
        " south ": " s ",
        " east ": " e ",
        " west ": " w ",
        "northwest": " nw ",
        "northeast": " ne ",
        "southwest": " sw ",
        "southeast": " se ",
    }

    value = f" {value} "

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(
        r"[^a-z0-9\s]",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    ).strip()

    return value


def similarity(a, b):
    """
    Return a name similarity score between 0 and 1.
    """

    if not a or not b:
        return 0

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


def prepare_website_data(df):
    """
    Add normalized fields to the website data.
    """

    df = df.copy()

    df["name_norm"] = df["name"].apply(
        normalize_text
    )

    df["street_norm"] = df["street"].apply(
        normalize_text
    )

    df["city_norm"] = df["city"].apply(
        normalize_text
    )

    df["state_norm"] = df["state"].apply(
        normalize_text
    )

    df["zip_norm"] = df["zip_code"].apply(
        normalize_text
    )

    return df


def prepare_crm_data(df):
    """
    Add normalized fields to the CRM data.
    """

    df = df.copy()

    df["name_norm"] = df["name"].apply(
        normalize_text
    )

    df["street_norm"] = df["billing_street"].apply(
        normalize_text
    )

    df["city_norm"] = df["billing_city"].apply(
        normalize_text
    )

    df["state_norm"] = df["billing_state"].apply(
        normalize_text
    )

    df["zip_norm"] = df["billing_zip"].apply(
        normalize_text
    )

    return df


def calculate_match_score(
    website_row,
    crm_row
):
    """
    Calculate how strongly a website community
    matches a CRM account.

    Address information gets more weight than
    the name because facility names can change.
    """

    score = 0
    reasons = []

    if (
        website_row["street_norm"]
        and website_row["street_norm"]
        == crm_row["street_norm"]
    ):
        score += 45
        reasons.append(
            "exact street match"
        )

    if (
        website_row["zip_norm"]
        and website_row["zip_norm"]
        == crm_row["zip_norm"]
    ):
        score += 25
        reasons.append(
            "exact ZIP match"
        )

    if (
        website_row["city_norm"]
        and website_row["city_norm"]
        == crm_row["city_norm"]
    ):
        score += 15
        reasons.append(
            "exact city match"
        )

    if (
        website_row["state_norm"]
        and website_row["state_norm"]
        == crm_row["state_norm"]
    ):
        score += 5
        reasons.append(
            "exact state match"
        )

    name_score = similarity(
        website_row["name_norm"],
        crm_row["name_norm"]
    )

    if name_score >= 0.90:
        score += 10
        reasons.append(
            f"very similar name ({name_score:.2f})"
        )

    elif name_score >= 0.75:
        score += 7
        reasons.append(
            f"similar name ({name_score:.2f})"
        )

    elif name_score >= 0.60:
        score += 3
        reasons.append(
            f"somewhat similar name ({name_score:.2f})"
        )

    return score, reasons


def is_credible_match(
    website_row,
    crm_row,
    score,
    reasons
):
    """
    Decide whether the best candidate is
    strong enough to be treated as a real match.

    We require multiple pieces of evidence.
    """

    street_match = (
        website_row["street_norm"] != ""
        and website_row["street_norm"]
        == crm_row["street_norm"]
    )

    zip_match = (
        website_row["zip_norm"] != ""
        and website_row["zip_norm"]
        == crm_row["zip_norm"]
    )

    city_match = (
        website_row["city_norm"] != ""
        and website_row["city_norm"]
        == crm_row["city_norm"]
    )

    name_score = similarity(
        website_row["name_norm"],
        crm_row["name_norm"]
    )

    if street_match and zip_match:
        return True

    if street_match and city_match:
        return True

    if (
        zip_match
        and city_match
        and name_score >= 0.75
    ):
        return True

    return False


def find_best_match(
    website_row,
    crm_df
):
    """
    Compare one website community against
    every CRM account and return the strongest match.
    """

    best_match = None
    best_score = -1
    best_reasons = []

    for _, crm_row in crm_df.iterrows():

        score, reasons = calculate_match_score(
            website_row,
            crm_row
        )

        if score > best_score:
            best_score = score
            best_match = crm_row
            best_reasons = reasons

    if best_match is None:
        return None

    credible = is_credible_match(
        website_row,
        best_match,
        best_score,
        best_reasons
    )

    return {
        "crm_account_id": best_match["account_id"],
        "crm_name": best_match["name"],
        "crm_parent_id": best_match["parent_id"],
        "crm_parent_name": best_match["parent_name"],
        "match_score": best_score,
        "match_reasons": "; ".join(
            best_reasons
        ),
        "credible_match": credible
    }


def match_all_communities(
    website_df,
    crm_df
):
    """
    Match every website community to the
    strongest CRM candidate.
    """

    website_df = prepare_website_data(
        website_df
    )

    crm_df = prepare_crm_data(
        crm_df
    )

    results = []

    for _, website_row in website_df.iterrows():

        match = find_best_match(
            website_row,
            crm_df
        )

        result = {
            "website_name": website_row["name"],
            "website_street": website_row["street"],
            "website_city": website_row["city"],
            "website_state": website_row["state"],
            "website_zip": website_row["zip_code"],
            "website_url": website_row["source_url"],
        }

        if match:
            result.update(match)

        else:
            result.update({
                "crm_account_id": None,
                "crm_name": None,
                "crm_parent_id": None,
                "crm_parent_name": None,
                "match_score": 0,
                "match_reasons": "",
                "credible_match": False
            })

        results.append(result)

    return pd.DataFrame(results)


if __name__ == "__main__":

    website_df = pd.read_csv(
        "website_locations.csv"
    )

    # This assumes crm.py has already been run
    # and we save the CRM data separately.
    crm_df = pd.read_csv(
        "crm_accounts.csv"
    )

    matches = match_all_communities(
        website_df,
        crm_df
    )

    print()
    print("=" * 50)
    print("MATCHING COMPLETE")
    print("=" * 50)

    print(
        "Website communities:",
        len(website_df)
    )

    print(
        "Credible matches:",
        matches["credible_match"].sum()
    )

    print(
        "No credible match:",
        (~matches["credible_match"]).sum()
    )

    print()
    print(
        matches[
            [
                "website_name",
                "crm_name",
                "crm_parent_name",
                "match_score",
                "credible_match"
            ]
        ].to_string(index=False)
    )

    matches.to_csv(
        "matching_results.csv",
        index=False
    )

    print()
    print(
        "Saved to: matching_results.csv"
    )