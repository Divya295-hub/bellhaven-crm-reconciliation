import pandas as pd


BELLHAVEN_PARENT_ID = "0015QAPLGS3FVYEEEM"
BELLHAVEN_PARENT_NAME = "Bellhaven Senior Living (Parent Account)"


def make_proposal(
    website_name,
    action,
    reason,
    crm_account_id=None,
    crm_name=None,
    old_parent=None,
    new_parent=None,
    lifetime_revenue=0,
    outstanding_ar=0,
    match_score=None,
    notes=None
):
    """
    Create one proposed CRM action.

    This function only creates a proposal.
    It does not make any CRM changes.
    """

    return {
        "website_name": website_name,
        "action": action,
        "reason": reason,
        "crm_account_id": crm_account_id,
        "crm_name": crm_name,
        "old_parent": old_parent,
        "new_parent": new_parent,
        "lifetime_revenue": lifetime_revenue,
        "outstanding_ar": outstanding_ar,
        "match_score": match_score,
        "notes": notes
    }


def choose_parent_action(lifetime_revenue, outstanding_ar):
    """
    Decide how to handle an account that should move to Bellhaven.

    If the account has both revenue history and outstanding AR,
    preserve the old account and create a new Bellhaven account.

    Otherwise, re-parent the existing account directly.
    """

    if lifetime_revenue > 0 and outstanding_ar > 0:
        return "CREATE_NEW_ACCOUNT_CHOW"

    return "REPARENT_EXISTING"


def load_data():
    """
    Load the website-to-CRM matching results and current CRM accounts.
    """

    matching_df = pd.read_csv("matching_results.csv")
    crm_df = pd.read_csv("crm_accounts.csv")

    return matching_df, crm_df


def clean_number(value):
    """
    Safely convert revenue/AR values to numbers.
    """

    if pd.isna(value):
        return 0

    try:
        return float(value)
    except (ValueError, TypeError):
        return 0


def get_crm_lookup(crm_df):
    """
    Create a quick lookup from CRM account ID to the current
    CRM account record.
    """

    lookup = {}

    for _, row in crm_df.iterrows():
        account_id = str(row.get("account_id", "")).strip()

        if account_id and account_id.lower() != "nan":
            lookup[account_id] = row

    return lookup


def build_parent_proposals(matching_df, crm_df):
    """
    Create proposals only when a credible website-to-CRM match
    needs a CRM parent correction.

    Current CRM data is used for parent, revenue, and AR values.
    """

    proposals = []

    crm_lookup = get_crm_lookup(crm_df)

    for _, match_row in matching_df.iterrows():

        if not bool(match_row.get("credible_match", False)):
            continue

        account_id = str(
            match_row.get("crm_account_id", "")
        ).strip()

        if not account_id or account_id.lower() == "nan":
            continue

        crm_row = crm_lookup.get(account_id)

        # If the matching file references an account that is no
        # longer present in the current CRM extract, don't make
        # an automatic proposal.
        if crm_row is None:
            continue

        current_parent_id = str(
            crm_row.get("parent_id", "")
        ).strip()

        current_parent_name = str(
            crm_row.get("parent_name", "")
        ).strip()

        if current_parent_id.lower() == "nan":
            current_parent_id = ""

        if current_parent_name.lower() == "nan":
            current_parent_name = ""

        # Already correctly assigned to Bellhaven.
        if current_parent_id == BELLHAVEN_PARENT_ID:
            continue

        if current_parent_name == BELLHAVEN_PARENT_NAME:
            continue

        lifetime_revenue = clean_number(
            crm_row.get("lifetime_revenue", 0)
        )

        outstanding_ar = clean_number(
            crm_row.get("outstanding_ar", 0)
        )

        # Missing parent.
        if not current_parent_id and not current_parent_name:

            action = "SET_PARENT"

            reason = (
                "The website identifies this community as part "
                "of Bellhaven, and the CRM account has no parent. "
                "The Bellhaven parent should be added."
            )

        else:

            action = choose_parent_action(
                lifetime_revenue,
                outstanding_ar
            )

            if action == "CREATE_NEW_ACCOUNT_CHOW":

                reason = (
                    "The website shows this community as part of "
                    "Bellhaven, but the CRM account has both revenue "
                    "history and outstanding AR. The old account "
                    "should be preserved under the billing SOP."
                )

            else:

                reason = (
                    "The website shows this community as part of "
                    "Bellhaven, but the CRM account is currently "
                    "under a different parent. The existing account "
                    "can be re-parented directly."
                )

        proposals.append(
            make_proposal(
                website_name=match_row.get("website_name"),
                action=action,
                reason=reason,
                crm_account_id=account_id,
                crm_name=crm_row.get("name"),
                old_parent=current_parent_name,
                new_parent=BELLHAVEN_PARENT_NAME,
                lifetime_revenue=lifetime_revenue,
                outstanding_ar=outstanding_ar,
                match_score=match_row.get("match_score"),
                notes=(
                    "Website used as evidence for current Bellhaven "
                    "ownership. Current CRM revenue and AR were used "
                    "to determine the safe CRM action."
                )
            )
        )

    return proposals


def build_unmatched_proposals(matching_df):
    """
    Create proposals for website communities that do not have
    a credible CRM match.

    Amberly Manor is intentionally sent to human research.
    Other unmatched locations can be proposed for account creation.
    """

    proposals = []

    for _, row in matching_df.iterrows():

        if bool(row.get("credible_match", False)):
            continue

        website_name = str(
            row.get("website_name", "")
        ).strip()

        if not website_name:
            continue

        # Amberly Manor has a same-name CRM account at a
        # completely different address/state.
        if website_name == "Amberly Manor":

            proposals.append(
                make_proposal(
                    website_name=website_name,
                    action="RESEARCH_NO_MATCH",
                    reason=(
                        "The website lists this community, but no "
                        "credible CRM match was found. A CRM account "
                        "exists with the same name but a different "
                        "address and state, so it should not be "
                        "automatically linked."
                    ),
                    notes=(
                        "Requires human research before creating "
                        "or changing a CRM account."
                    )
                )
            )

        else:

            proposals.append(
                make_proposal(
                    website_name=website_name,
                    action="CREATE_NEW_ACCOUNT",
                    reason=(
                        "The website lists this Bellhaven community, "
                        "but no credible CRM account was found. "
                        "A new CRM account should be created under "
                        "the Bellhaven parent after human approval."
                    ),
                    new_parent=BELLHAVEN_PARENT_NAME,
                    match_score=row.get("match_score"),
                    notes=(
                        "No credible existing CRM account was found."
                    )
                )
            )

    return proposals


def build_stale_account_proposals(matching_df, crm_df):
    """
    Find active CRM accounts currently under Bellhaven that do not
    have a credible match to a current website community.
    """

    proposals = []

    matched_account_ids = set(
        matching_df.loc[
            matching_df["credible_match"] == True,
            "crm_account_id"
        ]
        .dropna()
        .astype(str)
        .str.strip()
    )

    bellhaven_accounts = crm_df[
        crm_df["parent_id"].astype(str).str.strip()
        == BELLHAVEN_PARENT_ID
    ]

    for _, row in bellhaven_accounts.iterrows():

        account_id = str(
            row.get("account_id", "")
        ).strip()

        if not account_id:
            continue

        # This is a current website account, so it is not stale.
        if account_id in matched_account_ids:
            continue

        status = str(
            row.get("status", "")
        ).strip().lower()

        # Don't repeatedly propose already inactive records.
        if status == "inactive":
            continue

        duplicate_of = str(
            row.get("duplicate_of_account", "")
        ).strip()

        # Don't repeatedly propose an account already identified
        # as a duplicate.
        if duplicate_of and duplicate_of.lower() != "nan":
            continue

        lifetime_revenue = clean_number(
            row.get("lifetime_revenue", 0)
        )

        outstanding_ar = clean_number(
            row.get("outstanding_ar", 0)
        )

        if lifetime_revenue > 0 and outstanding_ar > 0:

            action = "CHOW_REVIEW"

            reason = (
                "This CRM account is under Bellhaven but does not "
                "appear on the current website. It has both revenue "
                "history and outstanding AR, so billing history "
                "should be preserved and the account requires "
                "CHOW review."
            )

        else:

            action = "STALE_ACCOUNT_REVIEW"

            reason = (
                "This CRM account is under Bellhaven but does not "
                "appear to have a credible match to a current "
                "website community. Human review is needed before "
                "changing it."
            )

        proposals.append(
            make_proposal(
                website_name="",
                action=action,
                reason=reason,
                crm_account_id=account_id,
                crm_name=row.get("name"),
                old_parent=row.get("parent_name"),
                new_parent=None,
                lifetime_revenue=lifetime_revenue,
                outstanding_ar=outstanding_ar,
                notes=(
                    "Reverse check: CRM account is under Bellhaven "
                    "but has no credible current website match."
                )
            )
        )

    return proposals


def build_duplicate_proposals(crm_df):
    """
    Find likely duplicate CRM accounts.

    A duplicate must have the same normalized name, address,
    city, state, ZIP, and parent.

    Already-inactive duplicates are ignored.
    """

    proposals = []

    duplicate_columns = [
        "name",
        "billing_street",
        "billing_city",
        "billing_state",
        "billing_zip",
        "parent_id"
    ]

    working_df = crm_df.copy()

    for column in duplicate_columns:

        working_df[f"{column}_norm"] = (
            working_df[column]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.strip()
        )

    normalized_columns = [
        f"{column}_norm"
        for column in duplicate_columns
    ]

    grouped = working_df.groupby(
        normalized_columns,
        dropna=False
    )

    for _, group in grouped:

        if len(group) < 2:
            continue

        active_group = group[
            group["status"]
            .fillna("")
            .astype(str)
            .str.lower()
            != "inactive"
        ]

        if len(active_group) < 2:
            continue

        survivor = active_group.iloc[0]

        for _, duplicate in active_group.iloc[1:].iterrows():

            proposals.append(
                make_proposal(
                    website_name="",
                    action="MARK_DUPLICATE_INACTIVE",
                    reason=(
                        "This CRM account appears to duplicate "
                        "another account with the same facility "
                        "details. The duplicate should be marked "
                        "inactive and linked to the surviving "
                        "account."
                    ),
                    crm_account_id=duplicate["account_id"],
                    crm_name=duplicate["name"],
                    old_parent=duplicate.get("parent_name"),
                    lifetime_revenue=clean_number(
                        duplicate.get("lifetime_revenue", 0)
                    ),
                    outstanding_ar=clean_number(
                        duplicate.get("outstanding_ar", 0)
                    ),
                    notes=(
                        f"Proposed survivor: "
                        f"{survivor['account_id']}"
                    )
                )
            )

    return proposals


def build_all_proposals():
    """
    Build the complete proposal queue from the current
    matching results and current CRM data.
    """

    matching_df, crm_df = load_data()

    proposals = []

    # Website -> CRM parent corrections
    proposals.extend(
        build_parent_proposals(
            matching_df,
            crm_df
        )
    )

    # Website locations with no credible CRM match
    proposals.extend(
        build_unmatched_proposals(
            matching_df
        )
    )

    # CRM -> website reverse check
    proposals.extend(
        build_stale_account_proposals(
            matching_df,
            crm_df
        )
    )

    # Duplicate detection
    proposals.extend(
        build_duplicate_proposals(
            crm_df
        )
    )

    return pd.DataFrame(proposals)


if __name__ == "__main__":

    proposals_df = build_all_proposals()

    print()
    print("=" * 50)
    print("PROPOSAL GENERATION COMPLETE")
    print("=" * 50)
    print("Total proposals:", len(proposals_df))
    print()

    if not proposals_df.empty:

        print(
            proposals_df[
                [
                    "website_name",
                    "action",
                    "crm_name",
                    "old_parent",
                    "new_parent"
                ]
            ].to_string(index=False)
        )

    proposals_df.to_csv(
        "final_proposals.csv",
        index=False
    )

    print()
    print("Saved to: final_proposals.csv")