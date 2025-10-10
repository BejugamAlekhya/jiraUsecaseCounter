import streamlit as st
from jira import JIRA

# --- Load Jira Credentials ---
jira_url = st.secrets["JIRA_URL"]
jira_email = st.secrets["JIRA_EMAIL"]
jira_api_token = st.secrets["JIRA_API_TOKEN"]
 
# --- Connect to Jira (Cached) ---
@st.cache_resource
def get_jira_connection():
    options = {"server": jira_url}
    return JIRA(options=options, basic_auth=(jira_email, jira_api_token))
# --- Get Issue Count ---
@st.cache_data(ttl=3600)
def get_use_case_count(jql_query):
    jira = get_jira_connection()
    issues = jira.search_issues(jql_query, maxResults=0)
    return issues.total
 
# --- Get All Issues with Pagination ---
@st.cache_data(ttl=3600)
def get_use_case_data(jql_query):
    jira = get_jira_connection()
    all_issues = []
    start = 0
    chunk_size = 100
    while True:
        issues = jira.search_issues(jql_query, startAt=start, maxResults=chunk_size)
        all_issues.extend(issues)
        if len(issues) < chunk_size:
            break
        start += chunk_size
    issue_list = [(issue.key, issue.fields.summary) for issue in all_issues]
    return issue_list 
    
# --- Streamlit UI ---
st.title("📊 Jira Use Case Counter")
st.markdown("Use filters below to generate a custom JQL and fetch the total number of use cases.")

# Sidebar filters
with st.sidebar:
    st.header("Filter Options")
    industry_options = [
        "Fashion (FSH)", "Food & Beverage (FAB)", "Chemicals (CHE)",
        "Distribution Enterprise (DSE)", "Equipment (EQP)"
    ]
    selected_industry = st.selectbox("Select Industry", industry_options)
    component_options = [
        "All", "Order to Cash", "Procure to Pay", "Financial Plan to Report",
        "Freight Costs to Charges", "Inspection to Approval", "Inventory to Managed Packages",
        "Plan to Inventory", "Production to Inventory", "Rental Agreement To Invoice",
        "Buy to Order", "Distribution to Internal Invoice"
    ]
    selected_component = st.selectbox("Select Component", component_options)
    status_options = {
        "Resolved & Reopened": ["Resolved", "Reopened"],
        "Resolved": ["Resolved"],
        "Reopened": ["Reopened"]
    }

    selected_status_label = st.selectbox("Select Status", list(status_options.keys()))
    selected_statuses = status_options[selected_status_label]
 
 
# --- Build JQL Query ---
project_name = "Industry Process Content Team"
product_value = "M3"

# Status clause
if len(selected_statuses) > 1:
    status_clause = f"status IN ({', '.join(selected_statuses)})"
else:
    status_clause = f"status = {selected_statuses[0]}"
# Component clause
if selected_component == "All":
    all_components = [
        "Buy to Order", "Distribution to Internal Invoice", "Inspection to Approval",
        "Inventory to Managed Packages", "Order to Cash", "Procure to Pay",
        "Financial Plan to Report", "Freight Costs to Charges", "Plan to Inventory",
        "Production to Inventory", "Rental Agreement To Invoice"
    ]
    component_clause = f"component IN ({', '.join([f'\"{c}\"' for c in all_components])})"
else:
    component_clause = f'component = "{selected_component}"'
    
# Final JQL
jql_query = (
    f'project = "{project_name}" '
    f'AND "product(s)[select list (multiple choices)]" = {product_value} '
    f'AND type = "Use Case" '
    f'AND "industry / cloudsuite categories[select list (multiple choices)]" = "{selected_industry}" '
    f'AND {component_clause} '
    f'AND {status_clause} '
    f'ORDER BY created DESC'
)

# --- Show JQL and Result Count ---
st.info(f"**Generated JQL:** `{jql_query}`")
with st.spinner("Fetching count from Jira..."):
    try:
        count = get_use_case_count(jql_query)
        st.metric(
            label=f"Total Use Cases in {selected_component} for {selected_industry} with {selected_status_label} status",
            value=count
        )
    except Exception as e:
        st.error("⚠️ Failed to fetch data from Jira.")
        st.exception(e)
        
# --- Show Issue List only if component is NOT 'All' ---
if selected_component != "All":
    with st.spinner("Fetching issue list from Jira..."):
        try:
            issues = get_use_case_data(jql_query)
            if issues:
                st.subheader("Jira Use Cases:")
                for key, summary in issues:
                    st.markdown(f"- **{key}** — {summary}")
            else:
                st.info("No issues found for the selected filters.")
        except Exception as e:
            st.error("⚠️ Error fetching issue details.")
            st.exception(e)
else:
    st.info("Issue details are hidden when 'All' components are selected. Showing only total count.")

 