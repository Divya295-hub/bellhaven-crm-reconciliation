import os
import requests
import pandas as pd


CRM_API_BASE = "https://analyst-assessment-production.up.railway.app/api/v1"
CRM_ACCOUNTS_URL = f"{CRM_API_BASE}/accounts"


def get_token():
    token = os.environ.get("CLIPBOARD_TOKEN")

    if not token:
        raise ValueError(
            "CLIPBOARD_TOKEN is not set. "
            "Please set your CRM token as an environment variable."
        )

    return token


def get_headers():
    return {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json"
    }


def get_crm_account(account_id):
    response = requests.get(
        f"{CRM_ACCOUNTS_URL}/{account_id}",
        headers=get_headers(),
        timeout=15
    )

    response.raise_for_status()

    return response.json()


def get_all_crm_accounts(page_size=50):
    all_accounts = []
    page = 1

    while True:
        print(f"Getting CRM page {page}...")

        response = requests.get(
            CRM_ACCOUNTS_URL,
            headers=get_headers(),
            params={
                "page": page,
                "page_size": page_size
            },
            timeout=15
        )

        response.raise_for_status()

        result = response.json()

        accounts = result["data"]

        all_accounts.extend(accounts)

        total_accounts = result["total"]

        print(
            f"  Retrieved {len(accounts)} accounts "
            f"(total collected: "
            f"{len(all_accounts)}/{total_accounts})"
        )

        if len(all_accounts) >= total_accounts:
            break

        page += 1

    return all_accounts


def get_crm_dataframe():
    accounts = get_all_crm_accounts()

    return pd.DataFrame(accounts)


def update_crm_account(account_id, payload):
    if not payload:
        raise ValueError(
            "Update payload cannot be empty."
        )

    response = requests.patch(
        f"{CRM_ACCOUNTS_URL}/{account_id}",
        headers=get_headers(),
        json=payload,
        timeout=15
    )

    response.raise_for_status()

    return response.json()


def create_crm_account(payload):
    if not payload:
        raise ValueError(
            "Create payload cannot be empty."
        )

    response = requests.post(
        CRM_ACCOUNTS_URL,
        headers=get_headers(),
        json=payload,
        timeout=15
    )

    response.raise_for_status()

    return response.json()


if __name__ == "__main__":
    crm_df = get_crm_dataframe()

    print()
    print("=" * 50)
    print("CRM EXTRACTION COMPLETE")
    print("=" * 50)
    print("Total CRM accounts:", len(crm_df))

    print()
    print("CRM columns:")
    print(crm_df.columns.tolist())
    
    print()
    print("First 10 CRM accounts:")
    print(crm_df.head(10).to_string(index=False))

    crm_df.to_csv(
        "crm_accounts.csv",
        index=False
    )

    print()
    print("Saved to: crm_accounts.csv")