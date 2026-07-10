from __future__ import annotations

from typing import Dict, List
import re

from .models import TaskSpec


DEFAULT_ALLOWED_ACTIONS = [
    "CLICK",
    "TYPE",
    "SCROLL",
    "NAVIGATE",
    "WAIT",
    "SELECT",
    "UPLOAD",
    "DOWNLOAD",
    "COPY_TEXT",
    "PASTE",
    "OPEN_TAB",
    "CLOSE_TAB",
    "EXTRACT_TEXT",
    "VERIFY_TEXT",
    "VERIFY_DOWNLOAD",
    "INSPECT_STATE",
    "STOP",
]

DEFAULT_FORBIDDEN_ACTIONS = [
    "DELETE",
    "MERGE",
]

DEFAULT_APPROVAL_REQUIRED_ACTIONS = [
    "ASK_HUMAN_APPROVAL",
]


_TASK_ROWS = [
    ("microsoft_word_supervised_actions", "Microsoft Word Supervised Actions", "microsoft word"),
    ("company_research", "Company Research", "company research"),
    ("crm_updates", "CRM Updates", "crm"),
    ("outlook_web_email_triage", "Outlook Web Email Triage", "email"),
    ("sharepoint_document_retrieval", "SharePoint Document Retrieval", "sharepoint"),
    ("vendor_portal_invoice_downloads", "Vendor Portal Invoice Downloads", "vendor portal"),
    ("bi_dashboard_export", "BI Dashboard Export", "analytics"),
    ("microsoft_forms_survey_creation", "Microsoft Forms Survey Creation", "forms"),
    ("teams_web_action_item_extraction", "Teams Web Action Item Extraction", "teams"),
    ("competitor_pricing_comparison", "Competitor Pricing Comparison", "market research"),
    ("linkedin_account_research", "LinkedIn Account Research", "social research"),
    ("applicant_tracking_workflows", "Applicant Tracking Workflows", "recruiting"),
    ("procurement_portal_workflows", "Procurement Portal Workflows", "procurement"),
    ("helpdesk_ticket_triage", "Helpdesk Ticket Triage", "support"),
    ("bank_portal_statement_downloads", "Bank Portal Statement Downloads", "banking"),
    ("payroll_record_checks", "Payroll Record Checks", "payroll"),
    ("learning_management_workflows", "Learning Management Workflows", "learning"),
    ("regulatory_research", "Regulatory Research", "compliance"),
    ("travel_comparison_without_booking", "Travel Comparison Without Booking", "travel"),
    ("hotel_comparison_without_payment", "Hotel Comparison Without Payment", "travel"),
    ("maps_and_route_research", "Maps and Route Research", "maps"),
    ("shopify_order_review", "Shopify Order Review", "commerce"),
    ("amazon_business_cart_preparation_without_checkout", "Amazon Business Cart Preparation Without Checkout", "commerce"),
    ("shipping_carrier_tracking", "Shipping Carrier Tracking", "logistics"),
    ("warehouse_order_review", "Warehouse Order Review", "warehouse"),
    ("supplier_lead_time_research", "Supplier Lead-Time Research", "supply chain"),
    ("erp_purchase_order_review", "ERP Purchase Order Review", "erp"),
    ("insurance_claim_lookup", "Insurance Claim Lookup", "insurance"),
    ("government_filing_draft_preparation_without_submission", "Government Filing Draft Preparation Without Submission", "government"),
    ("calendar_scheduling_draft_workflows", "Calendar Scheduling Draft Workflows", "calendar"),
    ("contract_repository_research", "Contract Repository Research", "legal ops"),
    ("market_size_research", "Market Size Research", "market research"),
    ("grant_opportunity_research", "Grant Opportunity Research", "grant research"),
    ("project_management_board_updates", "Project Management Board Updates", "project management"),
    ("jira_issue_updates", "Jira Issue Updates", "engineering"),
    ("github_issue_triage_without_merge", "GitHub Issue Triage Without Merge", "engineering"),
    ("azure_devops_backlog_creation", "Azure DevOps Backlog Creation", "engineering"),
    ("cloud_console_log_inspection_without_destructive_changes", "Cloud Console Log Inspection Without Destructive Changes", "cloud ops"),
    ("monitoring_dashboard_alert_review", "Monitoring Dashboard Alert Review", "operations"),
    ("api_documentation_research", "API Documentation Research", "developer research"),
    ("sandbox_checkout_testing", "Sandbox Checkout Testing", "qa"),
    ("careers_page_research", "Careers Page Research", "recruiting"),
    ("job_application_draft_without_final_submission", "Job Application Draft Without Final Submission", "recruiting"),
    ("university_portal_course_planning", "University Portal Course Planning", "education"),
    ("healthcare_portal_document_download_without_care_changes", "Healthcare Portal Document Download Without Care Changes", "healthcare"),
    ("patient_scheduling_options_without_final_booking", "Patient Scheduling Options Without Final Booking", "healthcare"),
    ("legal_research_without_legal_conclusions", "Legal Research Without Legal Conclusions", "legal research"),
    ("compliance_training_assignment", "Compliance Training Assignment", "compliance"),
    ("tax_document_download_without_filing", "Tax Document Download Without Filing", "tax"),
    ("benefits_plan_comparison", "Benefits Plan Comparison", "hr"),
    ("retirement_statement_download_without_investment_changes", "Retirement Statement Download Without Investment Changes", "finance"),
    ("vendor_onboarding_draft", "Vendor Onboarding Draft", "procurement"),
    ("sanctions_and_exclusion_database_checks", "Sanctions and Exclusion Database Checks", "compliance"),
    ("customer_portal_address_updates", "Customer Portal Address Updates", "customer portal"),
    ("billing_system_overdue_invoice_review", "Billing System Overdue Invoice Review", "billing"),
    ("stripe_payout_export", "Stripe Payout Export", "finance"),
    ("quickbooks_receipt_categorization", "QuickBooks Receipt Categorization", "accounting"),
    ("xero_low_risk_reconciliation", "Xero Low-Risk Reconciliation", "accounting"),
    ("budget_scenario_export", "Budget Scenario Export", "finance"),
    ("treasury_balance_viewing_without_funds_movement", "Treasury Balance Viewing Without Funds Movement", "treasury"),
    ("expense_platform_review_within_policy", "Expense Platform Review Within Policy", "finance"),
    ("social_media_scheduler_drafts_without_publishing", "Social Media Scheduler Drafts Without Publishing", "marketing"),
    ("ad_dashboard_reporting_without_budget_changes", "Ad Dashboard Reporting Without Budget Changes", "marketing"),
    ("meta_business_suite_comment_review", "Meta Business Suite Comment Review", "marketing"),
    ("cms_blog_drafts", "CMS Blog Drafts", "content"),
    ("wordpress_broken_link_updates", "WordPress Broken-Link Updates", "content"),
    ("webflow_staging_edits_without_publish", "Webflow Staging Edits Without Publish", "content"),
    ("analytics_traffic_comparison", "Analytics Traffic Comparison", "analytics"),
    ("seo_keyword_research", "SEO Keyword Research", "seo"),
    ("newsletter_draft_without_send", "Newsletter Draft Without Send", "marketing"),
    ("webinar_registration_draft", "Webinar Registration Draft", "events"),
    ("inventory_marketplace_research", "Inventory Marketplace Research", "inventory"),
    ("manufacturing_dashboard_review", "Manufacturing Dashboard Review", "manufacturing"),
    ("quality_management_nonconformance_notes", "Quality Management Nonconformance Notes", "quality"),
    ("maintenance_work_order_prioritization", "Maintenance Work Order Prioritization", "operations"),
    ("fleet_service_review", "Fleet Service Review", "fleet"),
    ("fuel_card_outlier_review", "Fuel Card Outlier Review", "fleet"),
    ("dispatch_board_updates", "Dispatch Board Updates", "logistics"),
    ("customs_brokerage_status_lookup", "Customs Brokerage Status Lookup", "logistics"),
    ("supplier_scorecard_export", "Supplier Scorecard Export", "procurement"),
    ("safety_incident_trend_review", "Safety Incident Trend Review", "safety"),
    ("internal_knowledge_base_search", "Internal Knowledge Base Search", "knowledge management"),
    ("sop_page_draft", "SOP Page Draft", "knowledge management"),
    ("password_manager_lookup_with_permission_only", "Password Manager Lookup With Permission Only", "security"),
    ("identity_access_review_with_escalation_for_privileged_access", "Identity Access Review With Escalation for Privileged Access", "security"),
    ("audit_log_export", "Audit Log Export", "security"),
    ("data_catalog_access_request", "Data Catalog Access Request", "data governance"),
    ("contract_renewal_reminder", "Contract Renewal Reminder", "legal ops"),
    ("esignature_envelope_preparation_without_send", "E-signature Envelope Preparation Without Send", "legal ops"),
    ("vendor_risk_questionnaire_draft", "Vendor Risk Questionnaire Draft", "risk"),
    ("policy_version_comparison", "Policy Version Comparison", "compliance"),
    ("public_procurement_notice_search", "Public Procurement Notice Search", "procurement"),
    ("rfp_download_and_deadline_extraction", "RFP Download and Deadline Extraction", "procurement"),
    ("customer_success_health_score_review", "Customer Success Health Score Review", "customer success"),
    ("survey_analytics_export", "Survey Analytics Export", "analytics"),
    ("call_transcript_objection_extraction", "Call Transcript Objection Extraction", "sales"),
    ("competitor_review_sentiment_classification", "Competitor Review Sentiment Classification", "market research"),
    ("daily_kpi_dashboard_review", "Daily KPI Dashboard Review", "operations"),
    ("workflow_automation_failure_inspection", "Workflow Automation Failure Inspection", "operations"),
    ("ai_agent_observability_failure_tagging", "AI Agent Observability Failure Tagging", "ai ops"),
    ("monthly_revenue_variance_workflow_with_verification_and_approval_gates", "Monthly Revenue Variance Workflow with Verification and Approval Gates", "finance"),
]


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _default_example_steps(name: str) -> List[Dict[str, str]]:
    return [
        {"action": "OPEN_TAB", "target": "about:blank", "value": ""},
        {"action": "NAVIGATE", "target": "search", "value": name},
        {"action": "WAIT", "target": "domcontentloaded", "value": ""},
        {"action": "EXTRACT_TEXT", "target": "body", "value": ""},
        {"action": "VERIFY_TEXT", "target": "result relevance", "value": name},
    ]


def _risk_level(name: str) -> str:
    risky_terms = ["bank", "payroll", "tax", "medical", "legal", "publish", "booking", "money", "insurance"]
    lowered = name.lower()
    return "high" if any(term in lowered for term in risky_terms) else "medium"


def _approval_actions_for(name: str) -> List[str]:
    lowered = name.lower()
    gates = ["ASK_HUMAN_APPROVAL"]
    if any(term in lowered for term in ["without", "draft", "review", "comparison", "lookup", "research", "inspection"]):
        return gates
    return gates + ["DOWNLOAD", "UPLOAD", "TYPE"]


def load_task_specs() -> Dict[str, TaskSpec]:
    specs: Dict[str, TaskSpec] = {}
    for row_id, name, domain in _TASK_ROWS:
        task_id = row_id or _slugify(name)
        specs[task_id] = TaskSpec(
            id=task_id,
            name=name,
            description=f"Long-horizon Edge workflow for {name.lower()}.",
            domain=domain,
            risk_level=_risk_level(name),
            required_inputs=["company", "date_range", "objective"],
            success_criteria=[
                "Target page state reached.",
                "Required extraction completed.",
                "No blocked action executed without approval.",
            ],
            forbidden_actions=DEFAULT_FORBIDDEN_ACTIONS,
            approval_required_actions=_approval_actions_for(name),
            allowed_actions=DEFAULT_ALLOWED_ACTIONS,
            verification_steps=[
                "Confirm URL or page title changed as expected.",
                "Confirm key text or table content is present.",
                "Confirm trace entry saved for each step.",
            ],
            recovery_behavior=[
                "Retry with alternate selector.",
                "Fallback to text-based locate and click.",
                "Ask for human approval when uncertainty remains.",
            ],
            timeout_behavior="Stop task and persist trace with failure reason.",
            example_steps=_default_example_steps(name),
        )
    return specs


def get_task(task_id: str) -> TaskSpec:
    catalog = load_task_specs()
    if task_id not in catalog:
        raise KeyError(f"Unknown task id: {task_id}")
    return catalog[task_id]


def resolve_task_id_from_text(text: str) -> str | None:
    query = str(text or "").strip().lower()
    if not query:
        return None

    query_tokens = set(re.findall(r"[a-z0-9]+", query))
    if not query_tokens:
        return None

    catalog = load_task_specs()
    best_id = None
    best_score = 0.0

    for task_id, spec in catalog.items():
        space = " ".join([task_id, spec.name, spec.description, spec.domain]).lower()
        task_tokens = set(re.findall(r"[a-z0-9]+", space))
        if not task_tokens:
            continue

        overlap = query_tokens.intersection(task_tokens)
        if not overlap:
            continue

        # Balanced overlap scoring to avoid always favoring very short/long tasks.
        precision = len(overlap) / max(1, len(query_tokens))
        recall = len(overlap) / max(1, len(task_tokens))
        score = (2 * precision * recall) / max(1e-9, (precision + recall))

        # Boost direct task-id/name phrase hits.
        if task_id.replace("_", " ") in query:
            score += 0.2
        if spec.name.lower() in query:
            score += 0.2

        if score > best_score:
            best_id = task_id
            best_score = score

    # Keep conservative threshold to avoid accidental task hijack.
    return best_id if best_score >= 0.12 else None
