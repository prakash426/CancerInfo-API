#!/usr/bin/env python3
"""
CIAPI-L004 Rights Acceptance Audit Tool

Executes deterministic validation of candidate documents against CIAPI-L004 acceptance criteria.
Truthfully reports:
- Engineering implementation status
- L004 final acceptance status
- Counts across all required evidence and decision fields
- Owner-approved eligible corpus vs unresolved decisions vs quarantined material
- Active acceptance blockers (missing owner review, unsubmitted third-party permissions)
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.ingestion.rights_inventory import audit_candidate_acceptance


def main() -> int:
    report = audit_candidate_acceptance()

    print("=" * 80)
    print("CIAPI-L004 CANDIDATE DOCUMENT RIGHTS ACCEPTANCE AUDIT")
    print("=" * 80)
    print(f"Total Candidate Documents:              {report['total_candidate_documents']}")
    print(f"  - With Rights Evidence URL:           {report['with_rights_evidence']}/{report['total_candidate_documents']}")
    print(f"  - With Permissible Use Decision:      {report['with_permissible_use']}/{report['total_candidate_documents']}")
    print(f"  - With Attribution Decision:          {report['with_attribution_decision']}/{report['total_candidate_documents']}")
    print(f"  - With Publication Status Decision:   {report['with_publication_decision']}/{report['total_candidate_documents']}")
    print(f"  - With Owner Review Date:             {report['with_review_date']}/{report['total_candidate_documents']}")
    print(f"  - With Decision Owner / Reviewer:     {report['with_decision_owner']}/{report['total_candidate_documents']}")
    print("-" * 80)
    print("VALIDATED CORPUS & DECISION STATUS BREAKDOWN:")
    print(f"  - Owner-Approved Eligible Corpus:     {report['owner_approved_eligible_corpus_count']}")
    print(f"  - Unresolved Candidate Decisions:     {report['unresolved_candidate_decisions_count']}")
    print(f"  - Unresolved Permission Decisions:    {report['unresolved_permission_decisions_count']}")
    print(f"  - Excluded / Quarantined Material:    {report['excluded_quarantined_documents_count']}")
    print(f"  - Excluded / Untracked in Database:   {report['excluded_untracked_documents_count']}")
    print("-" * 80)
    print("THIRD-PARTY PERMISSION WORKFLOW:")
    print(f"  - Requests Actually Submitted:        {report['permission_requests_submitted']}")
    print(f"  - Required, Not Submitted (WHO):      {report['permission_required_not_submitted']}")
    print("=" * 80)
    print("STATUS SUMMARY:")
    print(f"  Engineering Implementation Complete:  {report['engineering_implementation_complete']}")
    print(f"  Owner Review Completed:               {report['owner_review_completed']}")
    print(f"  Owner-Approved Corpus Decision:       {report['owner_corpus_decision']}")
    print(f"  L004 Acceptance Criteria Satisfied:   {report['l004_acceptance_satisfied']}")
    print("=" * 80)

    if report["blockers"]:
        print("\nOPEN ACCEPTANCE BLOCKERS:")
        for idx, blocker in enumerate(report["blockers"], 1):
            print(f"  [{idx}] {blocker}")

        print("\nACTION REQUIRED BY REPOSITORY OWNER (PRAKASH):")
        print("  To transition from OPEN to ACCEPTED:")
        print("  1. Inspect each candidate URL for third-party images, diagrams, or proprietary tables.")
        print("  2. Use record_owner_rights_review(url, reviewer='Jaya Prakash Merepala', db=session, commit=True, ...)")
        print("     to durably finalize decisions in the database.")
        print("  3. Submit formal permission inquiry to WHO permissions committee for WHO fact sheets.")
        print("  4. Provide explicit owner decision approving the publication-eligible corpus (status currently PENDING).")
        print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
