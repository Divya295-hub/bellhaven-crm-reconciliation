import os
import pandas as pd
import streamlit as st

from crm import (
    get_crm_account,
    update_crm_account,
    create_crm_account
)


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

PROPOSALS_FILE = "final_proposals.csv"
DECISIONS_FILE = "review_decisions.csv"

BELLHAVEN_PARENT_ID = "0015QAPLGS3FVYEEEM"
BELLHAVEN_PARENT_NAME = "Bellhaven Senior Living (Parent Account)"


# ---------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------

st.set_page_config(
    page_title="Bellhaven CRM Review",
    page_icon="🏥",
    layout="wide"
)

st.title("Bellhaven CRM Review")
st.write(
    "Review proposed CRM changes before anything is written "
    "to the CRM."
)


# ---------------------------------------------------------
# LOAD FILES
# ---------------------------------------------------------

def load_proposals():
    if not os.path.exists(PROPOSALS_FILE):
        st.error(
            f"Could not find {PROPOSALS_FILE}. "
            "Make sure it is in the project folder."
        )
        st.stop()

    return pd.read_csv(PROPOSALS_FILE)


def load_decisions():
    if not os.path.exists(DECISIONS_FILE):
        return pd.DataFrame(
            columns=[
                "proposal_index",
                "website_name",
                "action",
                "decision"
            ]
        )

    return pd.read_csv(DECISIONS_FILE)


def save_decision(
    proposal_index,
    website_name,
    action,
    decision
):
    decisions = load_decisions()

    new_decision = pd.DataFrame(
        [{
            "proposal_index": proposal_index,
            "website_name": website_name,
            "action": action,
            "decision": decision
        }]
    )

    decisions = pd.concat(
        [decisions, new_decision],
        ignore_index=True
    )

    decisions.to_csv(
        DECISIONS_FILE,
        index=False
    )


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def clean_number(value):
    if pd.isna(value):
        return 0

    try:
        return float(value)
    except (ValueError, TypeError):
        return 0


def format_money(value):
    value = clean_number(value)
    return f"${value:,.2f}"


def execute_proposal(row):
    """
    Execute an approved proposal against the CRM.

    This function is only called after the user clicks Approve.
    """

    action = str(row.get("action", "")).strip()

    account_id = str(
        row.get("crm_account_id", "")
    ).strip()

    if account_id.lower() == "nan":
        account_id = ""

    # -----------------------------------------------------
    # SET PARENT
    # -----------------------------------------------------

    if action == "SET_PARENT":

        if not account_id:
            raise ValueError(
                "No CRM account ID was provided."
            )

        update_crm_account(
            account_id,
            {
                "parent_id": BELLHAVEN_PARENT_ID,
                "note": (
                    "Parent updated to Bellhaven Senior Living "
                    "after approved website-to-CRM reconciliation."
                )
            }
        )

        return "CRM parent updated successfully."


    # -----------------------------------------------------
    # REPARENT EXISTING
    # -----------------------------------------------------

    if action == "REPARENT_EXISTING":

        if not account_id:
            raise ValueError(
                "No CRM account ID was provided."
            )

        update_crm_account(
            account_id,
            {
                "parent_id": BELLHAVEN_PARENT_ID,
                "note": (
                    "Account re-parented to Bellhaven Senior Living "
                    "after approved website-to-CRM reconciliation."
                )
            }
        )

        return "CRM account re-parented successfully."


    # -----------------------------------------------------
    # MARK DUPLICATE INACTIVE
    # -----------------------------------------------------

    if action == "MARK_DUPLICATE_INACTIVE":

        if not account_id:
            raise ValueError(
                "No duplicate account ID was provided."
            )

        notes = str(
            row.get("notes", "")
        )

        survivor_id = ""

        if "Proposed survivor:" in notes:
            survivor_id = notes.split(
                "Proposed survivor:"
            )[-1].strip()

        if not survivor_id:
            raise ValueError(
                "Could not identify the surviving account."
            )

        update_crm_account(
            account_id,
            {
                "status": "Inactive",
                "duplicate_of_account": survivor_id,
                "note": (
                    f"Marked inactive as duplicate of "
                    f"{survivor_id} after approved review."
                )
            }
        )

        return "Duplicate account marked inactive."


    # -----------------------------------------------------
    # CREATE NEW ACCOUNT
    # -----------------------------------------------------

    if action == "CREATE_NEW_ACCOUNT":

        website_name = str(
            row.get("website_name", "")
        ).strip()

        if not website_name:
            raise ValueError(
                "Website community name is missing."
            )

        payload = {
            "name": website_name,
            "parent_id": BELLHAVEN_PARENT_ID,
            "billing_street": "",
            "billing_city": "",
            "billing_state": "",
            "billing_zip": "",
            "status": "Active",
            "note": (
                "New Bellhaven account created after approved "
                "website-to-CRM reconciliation."
            ),
            "created_by_candidate": True
        }

        create_crm_account(payload)

        return "New Bellhaven CRM account created."


    # -----------------------------------------------------
    # CREATE NEW ACCOUNT + CHOW
    # -----------------------------------------------------

    if action == "CREATE_NEW_ACCOUNT_CHOW":

        if not account_id:
            raise ValueError(
                "No old CRM account ID was provided."
            )

        old_account = get_crm_account(account_id)

        website_name = str(
            row.get("website_name", "")
        ).strip()

        if not website_name:
            raise ValueError(
                "Website community name is missing."
            )

        payload = {
            "name": website_name,
            "parent_id": BELLHAVEN_PARENT_ID,
            "billing_street": old_account.get(
                "billing_street", ""
            ),
            "billing_city": old_account.get(
                "billing_city", ""
            ),
            "billing_state": old_account.get(
                "billing_state", ""
            ),
            "billing_zip": old_account.get(
                "billing_zip", ""
            ),
            "care_type": old_account.get(
                "care_type", ""
            ),
            "phone": old_account.get(
                "phone", ""
            ),
            "status": "Active",
            "note": (
                "Current Bellhaven account created under "
                "the CHOW SOP. Old account preserved because "
                "it has revenue history and outstanding AR."
            ),
            "created_by_candidate": True
        }

        new_account = create_crm_account(
            payload
        )

        new_account_id = new_account.get(
            "account_id"
        )

        if not new_account_id:
            raise ValueError(
                "New account was created but no account ID "
                "was returned."
            )

        update_crm_account(
            account_id,
            {
                "chow_current_account": new_account_id,
                "note": (
                    f"Current Bellhaven account is "
                    f"{new_account_id}. Old account preserved "
                    f"under the CHOW SOP."
                )
            }
        )

        return (
            f"New Bellhaven account created "
            f"({new_account_id}) and linked to the old account."
        )


    # -----------------------------------------------------
    # REVIEW-ONLY ACTIONS
    # -----------------------------------------------------

    if action in [
        "RESEARCH_NO_MATCH",
        "STALE_ACCOUNT_REVIEW",
        "CHOW_REVIEW"
    ]:
        raise ValueError(
            "This proposal is intentionally review-only and "
            "cannot be changed automatically."
        )


    raise ValueError(
        f"Unknown proposal action: {action}"
    )


# ---------------------------------------------------------
# LOAD CURRENT DATA
# ---------------------------------------------------------

proposals_df = load_proposals()
decisions_df = load_decisions()


# ---------------------------------------------------------
# REMOVE ALREADY DECIDED PROPOSALS
# ---------------------------------------------------------

decided_indexes = set()

if not decisions_df.empty:
    decided_indexes = set(
        decisions_df["proposal_index"]
        .astype(str)
        .tolist()
    )


pending_proposals = []

for index, row in proposals_df.iterrows():

    if str(index) not in decided_indexes:
        pending_proposals.append(
            (index, row)
        )


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

st.subheader("Review Queue")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Total proposals",
        len(proposals_df)
    )

with col2:
    st.metric(
        "Already decided",
        len(decided_indexes)
    )

with col3:
    st.metric(
        "Waiting for review",
        len(pending_proposals)
    )


st.divider()


# ---------------------------------------------------------
# NO PENDING PROPOSALS
# ---------------------------------------------------------

if not pending_proposals:

    st.success(
        "All current proposals have been reviewed."
    )

    st.write(
        "No additional CRM changes are waiting for approval."
    )

    st.stop()


# ---------------------------------------------------------
# REVIEW EACH PROPOSAL
# ---------------------------------------------------------

for proposal_index, row in pending_proposals:

    website_name = str(
        row.get("website_name", "")
    ).strip()

    action = str(
        row.get("action", "")
    ).strip()

    crm_name = str(
        row.get("crm_name", "")
    ).strip()

    reason = str(
        row.get("reason", "")
    ).strip()

    old_parent = str(
        row.get("old_parent", "")
    ).strip()

    new_parent = str(
        row.get("new_parent", "")
    ).strip()

    crm_account_id = str(
        row.get("crm_account_id", "")
    ).strip()

    lifetime_revenue = clean_number(
        row.get("lifetime_revenue", 0)
    )

    outstanding_ar = clean_number(
        row.get("outstanding_ar", 0)
    )

    match_score = row.get(
        "match_score",
        ""
    )

    notes = str(
        row.get("notes", "")
    ).strip()


    # -----------------------------------------------------
    # CARD
    # -----------------------------------------------------

    st.markdown("---")

    title = website_name

    if not title:
        title = crm_name

    st.subheader(title)

    st.write(
        f"**Proposed action:** `{action}`"
    )


    # -----------------------------------------------------
    # EVIDENCE
    # -----------------------------------------------------

    st.markdown("### Evidence")

    if website_name:
        st.write(
            f"**Website community:** {website_name}"
        )

    if crm_name and crm_name.lower() != "nan":
        st.write(
            f"**CRM account:** {crm_name}"
        )

    if crm_account_id and crm_account_id.lower() != "nan":
        st.write(
            f"**CRM account ID:** {crm_account_id}"
        )

    if old_parent and old_parent.lower() != "nan":
        st.write(
            f"**Current CRM parent:** {old_parent}"
        )

    if new_parent and new_parent.lower() != "nan":
        st.write(
            f"**Proposed parent:** {new_parent}"
        )

    if match_score and str(match_score).lower() != "nan":
        st.write(
            f"**Match score:** {match_score}"
        )

    st.write(
        f"**Lifetime revenue:** "
        f"{format_money(lifetime_revenue)}"
    )

    st.write(
        f"**Outstanding AR:** "
        f"{format_money(outstanding_ar)}"
    )


    # -----------------------------------------------------
    # REASON
    # -----------------------------------------------------

    st.markdown("### Why this was proposed")

    st.write(reason)


    if notes and notes.lower() != "nan":
        st.markdown("### Notes")
        st.write(notes)


    # -----------------------------------------------------
    # REVIEW-ONLY WARNING
    # -----------------------------------------------------

    review_only = action in [
        "RESEARCH_NO_MATCH",
        "STALE_ACCOUNT_REVIEW",
        "CHOW_REVIEW"
    ]


    if review_only:

        st.warning(
            "This item is intentionally review-only. "
            "The app will not make an automatic CRM change."
        )

        st.info(
            "Use your research process to decide what should "
            "happen to this account."
        )

        continue


    # -----------------------------------------------------
    # APPROVE / REJECT
    # -----------------------------------------------------

    col_a, col_b = st.columns(2)


    with col_a:

        approve_button = st.button(
            "Approve",
            key=f"approve_{proposal_index}",
            type="primary"
        )


    with col_b:

        reject_button = st.button(
            "Reject",
            key=f"reject_{proposal_index}"
        )


    # -----------------------------------------------------
    # APPROVAL
    # -----------------------------------------------------

    if approve_button:

        try:

            result = execute_proposal(row)

            save_decision(
                proposal_index,
                website_name,
                action,
                "APPROVED"
            )

            st.success(
                f"Approved successfully. {result}"
            )

            st.rerun()

        except Exception as e:

            st.error(
                f"The CRM update failed: {e}"
            )

            st.warning(
                "The proposal was NOT recorded as approved."
            )


    # -----------------------------------------------------
    # REJECTION
    # -----------------------------------------------------

    if reject_button:

        save_decision(
            proposal_index,
            website_name,
            action,
            "REJECTED"
        )

        st.info(
            "Proposal rejected. No CRM change was made."
        )

        st.rerun()