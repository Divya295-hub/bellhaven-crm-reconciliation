# Bellhaven CRM Reconciliation



A small Python project for comparing Bellhaven Senior Living's current communities with CRM accounts and reviewing proposed ownership changes before they are written to the CRM.



## What this project does



Long-term care facilities can change ownership, names, or operating structures. When that happens, CRM records can become outdated or end up connected to the wrong parent company.



This project helps identify those differences by:



1. Collecting the current Bellhaven communities from the website.

2. Pulling the Bellhaven-related CRM accounts.

3. Matching website communities to CRM accounts using address, ZIP code, city, state, and name.

4. Identifying ownership or data issues that need attention.

5. Applying the CRM billing/CHOW rules when deciding what action is safe.

6. Sending proposed changes to a small review app.

7. Requiring human approval before making CRM changes.



The goal is not to automatically change everything that looks different. The goal is to make the differences easy to review and act on safely.







## Project structure



```text

bellhaven-crm-reconciliation/

│

├── data/

│

├── docs/

│   └── assessment\_writeup.md

│

├── src/

│   ├── crm.py

│   ├── matching.py

│   ├── proposals.py

│   ├── review\_app.py

│   └── scraper.py

│

├── tests/

│   └── test\_matching.py

│

├── .gitignore

├── README.md

└── requirements.txt

```







## How the workflow works



```text

Bellhaven Website

     ↓
 scraper.py

     ↓

website\_locations.csv

     ↓

matching.py

     ↓

matching\_results.csv

     ↑

  crm.py

     ↑

crm\_accounts.csv

     ↓

proposals.py

     ↓

final\_proposals.csv

     ↓

review\_app.py

     ↓

Human Approval

     ↓

  CRM API

```



Each part has a separate responsibility so that data collection, matching, proposal generation, and CRM updates are not mixed together.







## 1. Website scraping



`scraper.py` starts from both the Bellhaven homepage and the communities directory.



This was important because the homepage contained a current community that was not included in the main directory listing.



The scraper follows community links and pagination and collects:


<ul>
  <li>Community name</li>
  <li>Street address</li>
  <li>City</li>
  <li>State</li>
  <li>ZIP code</li>
  <li>Care offerings</li>
</ul>




The scraper found \*\*35 Bellhaven communities\*\*.



The results are saved to:



```text

website\_locations.csv

```







## 2. CRM extraction



`crm.py` connects to the CRM API using the candidate token stored in the `CLIPBOARD\_TOKEN` environment variable.



It retrieves all CRM accounts through the paginated API rather than relying on a single page of results.



The original CRM extract contained \*\*121 accounts\*\*.



The CRM data includes fields such as:


<ul>
  <li>Account ID</li>
  <li>Account name</li>
  <li>Parent account</li>
  <li>Address</li>
  <li>Care type</li>
  <li>Status</li>
  <li>Lifetime revenue</li>
  <li>Outstanding AR</li>
  <li>CHOW information</li>
  <li>Duplicate information</li>
  <li>Notes</li>
</ul>


The original CRM extract is saved as:



```text

crm\_accounts.csv

```



The project does not store the API token in the repository.







## 3. Matching website communities to CRM accounts



`matching.py` compares each website community with CRM accounts.



The matching logic gives the most weight to location information because addresses are generally more useful for identifying a facility than names alone.



The current scoring uses:

<ul>
  <li>Exact street match: 45 points</li>
  <li>Exact ZIP match: 25 points</li>
  <li>Exact city match: 15 points</li>
  <li>Exact state match: 5 points</li>
  <li>Very similar name: 10 points</li>
  <li>Similar name: 7 points</li>
  <li>Somewhat similar name: 3 points</li>
</ul>

A match is considered credible when there is enough location evidence, such as:

<ul>
  <li>Matching street and ZIP</li>
  <li>Matching street and city</li>
  <li>Matching ZIP and city with a sufficiently similar name</li>
</ul>


This helps avoid incorrectly linking two facilities just because their names look similar.



The results are saved to:



```text

matching\_results.csv

```







## 4. Parent ownership decisions



The website was treated as the best source for Bellhaven's current public footprint and current facility details.



The CRM was treated as the source for CRM-specific information such as:

<ul>
  <li>Account IDs</li>
  <li>Revenue history</li>
  <li>Outstanding AR</li>
  <li>Historical relationships</li>
  <li>Duplicate information</li>
  <li>CHOW information</li>
</ul>


This distinction matters because a website can show the current ownership relationship while the CRM still needs to preserve an older account for billing purposes.



In other words:



\*\*Knowing the current owner does not automatically mean the old CRM account can be overwritten.\*\*







## 5. CHOW and billing rule



Before changing the parent of a CRM account, the project checks:

<ul>
  <li>Lifetime revenue</li>
  <li>Outstanding AR</li>
</ul>


If an account has \*\*both\*\*:



```text

lifetime\_revenue > 0

AND

outstanding\_ar > 0

```



the old account is preserved.



Instead, the process creates a new account under Bellhaven and links the old account to the new account using:



```text

chow\_current\_account

```



If the account does not have both revenue history and outstanding AR, the existing account can be re-parented directly.



This prevents historical billing information from being lost.







## 6. Reverse CRM check



The reconciliation also works in the other direction.



It checks CRM accounts that are currently under Bellhaven and asks:



> Does this account still appear as a current Bellhaven community on the website?



This identified several accounts that did not have a credible current website match.



These were not automatically deleted or changed. They were placed into review because a missing website match can have several explanations, including a sale, closure, name change, or incomplete website information.







## 7. Duplicate handling



The CRM data also contained possible duplicate accounts.



The project looks for records with matching facility details such as:


<ul>
  <li>Name</li>
  <li>Address</li>
  <li>City</li>
  <li>State</li>
  <li>ZIP</li>
  <li>Parent</li>
</ul>


Only the clearest duplicate case was automatically proposed.



For that case, the surviving account was kept active and the duplicate account was:

\* Marked `Inactive`

\* Linked using `duplicate\_of\_account`

\* Given a note explaining the decision
</ul>


The project does not merge or delete CRM accounts.







## 8. Proposal queue



The initial reconciliation produced \*\*14 proposals\*\*.



These included:

<ul>
  <li>Existing accounts that could be re-parented</li>
  <li>Accounts requiring CHOW handling</li>
  <li>An account missing a parent</li>
  <li>New accounts for website communities without credible CRM matches</li>
  <li>Accounts requiring research</li>
  <li>Stale CRM accounts</li>
  <li>A duplicate account</li>
</ul>


Of the initial proposals, \*\*10 appropriate CRM changes were approved and processed\*\*.



The remaining \*\*4 cases were intentionally left for human research\*\*:

<ul>
  <li>Amberly Manor</li>
  <li>Bellhaven Care Center of Alliance</li>
  <li>Bellhaven of Coldwater</li>
  <li>Bellhaven of Sandusky</li>
</ul>


These cases were not automatically changed because the available evidence was not strong enough to justify a safe automated action.







## 9. Human review app



`review\_app.py` provides a simple Streamlit review screen.



For each executable proposal, the reviewer can see:

<ul>
  <li>Website community</li>
  <li>CRM account</li>
  <li>Account ID</li>
  <li>Current parent</li>
  <li>Proposed parent</li>
  <li>Match score</li>
  <li>Lifetime revenue</li>
  <li>Outstanding AR</li>
  <li>Reason for the proposal</li>
  <li>Supporting notes</li>
</ul>


The reviewer can then:



\*\*Approve\*\*



The approved action is sent to the CRM API.



\*\*Reject\*\*



The proposal is recorded as rejected and no CRM change is made.



Review-only cases are shown to the reviewer but cannot be automatically changed.



This creates an important safety boundary:



> No CRM write happens just because the matching logic produced a proposal.



A human must approve the change first.







## 10. Rerun behavior



The review app keeps a record of decisions in:



```text

review\_decisions.csv

```



Once a proposal has been approved or rejected, the app does not show that same proposal again during normal reruns.



The proposal generator also uses the current CRM state. This means accounts that have already been correctly re-parented are not proposed again.



For a production version, I would replace the CSV decision log with a stable proposal ID and a small database so that decisions remain tied to the underlying account/action even if the proposal order changes.







## 11. Running the project



### Install dependencies



From the project folder:



```cmd

pip install -r requirements.txt

```



### Set the CRM token



The CRM token should be stored as an environment variable rather than committed to GitHub.



On Windows CMD:



```cmd

set CLIPBOARD\_TOKEN=YOUR\_TOKEN\_HERE

```



### Run the scraper



```cmd

python src\\scraper.py

```



This creates:



```text

website\_locations.csv

```



### Pull CRM data



```cmd

python src\\crm.py

```



This creates:



```text

crm\_accounts.csv

```



### Run matching



```cmd

python src\\matching.py

```



This creates:



```text

matching\_results.csv

```



### Generate proposals



```cmd

python src\\proposals.py

```



This creates:



```text

final\_proposals.csv

```



### Start the review app



From the main project folder:



```cmd

streamlit run src\\review\_app.py

```



The app will open locally in the browser.







## 12. Safety considerations



The project is designed around a few simple safeguards:

<ul>
  <li>CRM writes only happen after human approval.</li>
  <li>API credentials are stored outside the repository.</li>
  <li>Accounts are not deleted or merged.</li>
  <li>Revenue and outstanding AR are checked before changing ownership.</li>
  <li>CHOW cases preserve the historical account.</li>
  <li>Uncertain matches are sent for review instead of being forced.</li>
  <li>Already-decided proposals are not repeatedly shown by the review app.</li>
</ul>





## 13. What I would improve for production



If this were moved beyond the assessment, I would make a few improvements:



### Stable proposal IDs



Each proposal should have an ID based on the account, proposed action, and relevant evidence rather than relying on its row number.



### Persistent decision storage



A small database would be safer than a CSV for tracking approvals and rejections.



### Better automated tests



The matching and CHOW decision rules should have tests for edge cases such as:

<ul>
  <li>Same address but different facility</li>
  <li>Name changes</li>
  <li>Missing ZIP codes</li>
  <li>Duplicate accounts</li>
  <li>Revenue with no AR</li>
  <li>AR with no revenue</li>
  <li>Both revenue and AR</li>
</ul>


### Monitoring



A scheduled run should produce a short summary showing:

<ul>
  <li>Number of website communities</li>
  <li>Number of CRM accounts</li>
  <li>Number of matches</li>
  <li>Number of new proposals</li>
  <li>Number of unresolved cases</li>
  <li>Number of CRM updates</li>
</ul>


This would make it easier to notice if the website structure or CRM API changed.







## Final note



The main design choice in this project was to separate \*\*finding differences\*\* from \*\*making changes\*\*.



The scraper and matching logic can identify what looks different, but the review layer decides what is safe to change.



That makes the process more useful for sales operations because the goal is not simply to make the CRM look like the website. The goal is to keep the CRM accurate while preserving the historical and billing information that still matters to the business.



