"""Job ranking and filtering to find the best matches."""
import re
from typing import List, Optional
from dataclasses import dataclass

from scrapers import Job
from config import config
from resume_manager import resume_manager, JobFitScore


@dataclass
class ScoredJob:
    """Job with relevance score and fit analysis."""
    job: Job
    score: float
    reasons: List[str]
    fit_score: Optional[JobFitScore] = None


def calculate_job_score(job: Job) -> ScoredJob:
    """Score a job based on relevance to preferences."""
    score = 0.0
    reasons = []

    title_lower = job.title.lower()
    company_lower = job.company.lower()

    # === Title Match Scoring ===

    # Exact role matches (highest value)
    priority_keywords = [
        ("it support", 30),
        ("help desk", 25),
        ("desktop support", 25),
        ("service desk", 25),
        ("customer experience", 30),
        ("cx support", 30),
        ("customer support lead", 35),
        ("ai integration", 40),
        ("ai support", 35),
        ("technical support", 20),
        ("support lead", 30),
        ("support manager", 30),
        ("support specialist", 20),
        ("support analyst", 20),
    ]

    for keyword, points in priority_keywords:
        if keyword in title_lower:
            score += points
            reasons.append(f"Title match: '{keyword}'")
            break  # Only count best match

    # Seniority level bonus
    if any(term in title_lower for term in ["lead", "senior", "manager", "ii", "iii"]):
        score += 10
        reasons.append("Leadership/Senior role")
    elif any(term in title_lower for term in ["junior", "entry", "associate", "i "]):
        score += 5
        reasons.append("Entry-level friendly")

    # === Salary Scoring ===
    if job.salary:
        score += 15
        reasons.append("Salary listed")

        # Try to extract salary number
        salary_match = re.search(r'\$?([\d,]+)', job.salary.replace(',', ''))
        if salary_match:
            try:
                salary_num = int(salary_match.group(1).replace(',', ''))
                if salary_num >= 90000:
                    score += 20
                    reasons.append("High salary ($90k+)")
                elif salary_num >= 70000:
                    score += 10
                    reasons.append("Good salary ($70k+)")
            except:
                pass

    # === Location Scoring (Bayonne, NJ - 5-30 mile radius for NJ, Manhattan/Brooklyn only for NY) ===
    location_lower = job.location.lower()

    if "remote" in location_lower:
        score += 20
        reasons.append("Remote - work from home")
    elif "hybrid" in location_lower:
        score += 15
        reasons.append("Hybrid option")

    # NJ locations within 5-30 miles of Bayonne ONLY
    # Close NJ (5-15 mi)
    close_nj = ["bayonne", "jersey city", "hoboken", "newark", "secaucus", "kearny",
                "harrison", "union city", "west new york", "north bergen"]
    # Medium NJ (15-30 mi)
    medium_nj = ["elizabeth", "fort lee", "hackensack", "englewood", "paramus",
                 "clifton", "passaic", "paterson", "east orange", "orange",
                 "irvington", "bloomfield", "montclair", "linden", "rahway",
                 "cranford", "woodbridge", "edison"]
    # Far NJ (>30 mi) - EXCLUDED
    excluded_nj = ["morristown", "parsippany", "wayne", "new brunswick", "perth amboy",
                   "trenton", "princeton", "somerset", "toms river"]

    # NY locations - ONLY Manhattan and Brooklyn allowed
    valid_nyc = ["manhattan", "brooklyn"]
    # Excluded NYC boroughs
    excluded_nyc = ["queens", "bronx", "staten island"]

    # Apply location scoring
    location_matched = False

    # Check for excluded NJ locations first (>30 mi)
    if any(loc in location_lower for loc in excluded_nj):
        score -= 20
        reasons.append("NJ too far (>30 mi) - excluded")
        location_matched = True
    # Check NJ locations (5-30 mile radius only)
    elif any(loc in location_lower for loc in close_nj):
        score += 25
        reasons.append("NJ close (5-15 mi)")
        location_matched = True
    elif any(loc in location_lower for loc in medium_nj):
        score += 18
        reasons.append("NJ medium (15-30 mi)")
        location_matched = True

    # Check NYC - only Manhattan and Brooklyn
    if not location_matched:
        if any(loc in location_lower for loc in valid_nyc):
            score += 20
            reasons.append(f"NYC ({[loc for loc in valid_nyc if loc in location_lower][0].title()})")
            location_matched = True
        elif any(loc in location_lower for loc in excluded_nyc):
            score -= 15  # Penalize excluded NYC boroughs
            reasons.append("NYC excluded borough (Queens/Bronx/SI)")
            location_matched = True
        elif "new york" in location_lower or "nyc" in location_lower:
            # Generic "New York" - assume could be Manhattan
            score += 10
            reasons.append("NYC (unspecified)")
            location_matched = True

    # Generic NJ
    if not location_matched:
        if "nj" in location_lower or "new jersey" in location_lower:
            score += 12
            reasons.append("NJ area")
            location_matched = True

    # Unknown/other location
    if not location_matched and "remote" not in location_lower and "hybrid" not in location_lower:
        score -= 10
        reasons.append("Location outside target area")

    # === Company Scoring ===

    # Well-known tech companies (bonus)
    good_companies = [
        "google", "microsoft", "amazon", "meta", "apple", "netflix",
        "salesforce", "adobe", "ibm", "oracle", "cisco", "dell",
        "hp", "intel", "nvidia", "zoom", "slack", "dropbox",
        "stripe", "square", "shopify", "twilio", "datadog",
    ]
    if any(company in company_lower for company in good_companies):
        score += 15
        reasons.append("Top tech company")

    # Avoid staffing agencies (lower priority)
    staffing_keywords = ["staffing", "recruiting", "talent", "consultants", "solutions"]
    if any(kw in company_lower for kw in staffing_keywords):
        score -= 10
        reasons.append("Staffing agency (lower priority)")

    # === Career Growth Potential ===
    # Roles that lead to advancement in IT

    growth_roles = [
        ("lead", 15, "Leadership path"),
        ("manager", 12, "Management track"),
        ("analyst", 10, "Analytical skills"),
        ("engineer", 12, "Engineering path"),
        ("specialist", 8, "Specialist role"),
        ("administrator", 10, "Admin experience"),
        ("coordinator", 5, "Coordination skills"),
    ]

    for keyword, points, reason in growth_roles:
        if keyword in title_lower:
            score += points
            reasons.append(f"Growth: {reason}")
            break

    # Companies known for good IT career development
    growth_companies = [
        "google", "microsoft", "amazon", "meta", "apple",
        "ibm", "accenture", "deloitte", "pwc", "kpmg",
        "jpmorgan", "goldman", "citi", "bank of america",
        "verizon", "at&t", "comcast",
    ]
    if any(company in company_lower for company in growth_companies):
        score += 10
        reasons.append("Strong IT career path")

    # === Interview Likelihood ===
    # Factors that increase chance of getting an interview

    # Direct employer (not staffing) = higher callback rate
    staffing_agencies = ["staffing", "recruiting", "talent", "consultants",
                         "solutions", "manpower", "randstad", "robert half",
                         "teksystems", "insight global", "kforce"]
    is_staffing = any(agency in company_lower for agency in staffing_agencies)

    if not is_staffing:
        score += 10
        reasons.append("Direct employer")
    else:
        score -= 5
        reasons.append("Staffing agency")

    # Entry/mid level = more likely to interview
    if any(term in title_lower for term in ["entry", "junior", "associate", "i ", " i,"]):
        score += 8
        reasons.append("Entry-friendly")

    # === Negative Scoring ===

    # Unrelated roles to filter out
    avoid_keywords = ["intern", "director", "vp", "vice president", "chief", "cto", "cio"]
    if any(kw in title_lower for kw in avoid_keywords):
        score -= 20
        reasons.append("Role level mismatch")

    # Sales/Marketing/Non-IT roles to exclude
    exclude_roles = [
        "sales", "marketing", "account executive", "account manager",
        "customer success manager", "csm", "success manager",
        "business development", "recruiter", "hr ",
    ]
    if any(kw in title_lower for kw in exclude_roles):
        score -= 50
        reasons.append("Not an IT/Support role")

    # Requires too much experience
    if any(term in title_lower for term in ["senior", "sr.", "principal", "staff"]):
        score -= 5  # Small penalty - still might be worth applying

    # === Resume-Based Fit Scoring ===
    fit_score = None
    if resume_manager.has_resume():
        fit_score = resume_manager.calculate_fit_score(
            job_title=job.title,
            job_description=job.description_snippet or "",
            job_location=job.location,
            job_company=job.company
        )

        # Add fit score to overall ranking (weighted)
        # Fit score is 0-100, scale it to add 0-50 points
        fit_bonus = fit_score.overall_score * 0.5
        score += fit_bonus

        if fit_score.overall_score >= 75:
            reasons.append(f"Resume fit: {fit_score.get_fit_label()} ({fit_score.overall_score}%)")
        elif fit_score.overall_score >= 50:
            reasons.append(f"Resume fit: {fit_score.overall_score}%")

        # Add top fit reasons
        if fit_score.reasons:
            reasons.extend(fit_score.reasons[:2])

    return ScoredJob(job=job, score=score, reasons=reasons, fit_score=fit_score)


def rank_jobs(jobs: List[Job], max_results: int = 15, return_scored: bool = False):
    """Rank jobs and return top matches.

    Args:
        jobs: List of jobs to rank
        max_results: Maximum number of jobs to return
        return_scored: If True, return ScoredJob objects with fit scores

    Returns:
        List of Job or ScoredJob objects depending on return_scored
    """
    if not jobs:
        return []

    # Score all jobs
    scored_jobs = [calculate_job_score(job) for job in jobs]

    # Sort by score descending
    scored_jobs.sort(key=lambda x: x.score, reverse=True)

    # Filter out negative scores (poor matches)
    good_jobs = [sj for sj in scored_jobs if sj.score > 0]

    # Return top N
    top_jobs = good_jobs[:max_results]

    # Print ranking for debugging
    print(f"\nJob Ranking (showing top {len(top_jobs)}):")
    print("-" * 50)
    for i, sj in enumerate(top_jobs, 1):
        fit_str = ""
        if sj.fit_score:
            fit_str = f" | Fit: {sj.fit_score.overall_score}% {sj.fit_score.get_emoji_rating()}"
        print(f"{i}. [{sj.score:.0f}] {sj.job.title} @ {sj.job.company}{fit_str}")
        print(f"   Reasons: {', '.join(sj.reasons[:3])}")

    if return_scored:
        return top_jobs
    return [sj.job for sj in top_jobs]


def rank_jobs_with_scores(jobs: List[Job], max_results: int = 15) -> List[ScoredJob]:
    """Rank jobs and return ScoredJob objects with fit scores."""
    return rank_jobs(jobs, max_results, return_scored=True)


def get_daily_job_limit() -> int:
    """Get max jobs to send per run."""
    return 12  # Sweet spot: not too many, not too few


if __name__ == "__main__":
    # Test with sample jobs
    from scrapers import Job

    test_jobs = [
        Job("1", "IT Support Specialist", "Google", "Remote", "$85,000", "http://...", "linkedin"),
        Job("2", "Sales Representative", "Staffing Co", "NYC", None, "http://...", "linkedin"),
        Job("3", "Customer Experience Lead", "Stripe", "New York, NY (Hybrid)", "$95,000", "http://...", "linkedin"),
        Job("4", "Help Desk Technician", "Random Corp", "Brooklyn", None, "http://...", "indeed"),
        Job("5", "AI Integration Support Engineer", "Microsoft", "Remote", "$120,000", "http://...", "linkedin"),
    ]

    ranked = rank_jobs(test_jobs, max_results=3)
    print(f"\nTop {len(ranked)} jobs selected")
