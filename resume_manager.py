"""Resume management and job fit scoring."""
import os
import re
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Set, Dict
from datetime import datetime


@dataclass
class Resume:
    """Parsed resume data."""
    raw_text: str
    skills: List[str] = field(default_factory=list)
    job_titles: List[str] = field(default_factory=list)
    experience_years: int = 0
    education: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    keywords: Set[str] = field(default_factory=set)
    last_updated: str = ""

    def __post_init__(self):
        if isinstance(self.keywords, list):
            self.keywords = set(self.keywords)


@dataclass
class CurrentJob:
    """User's current job description for matching."""
    title: str = ""
    description: str = ""
    skills: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)


@dataclass
class JobFitScore:
    """Job fit analysis result."""
    overall_score: int  # 0-100
    skill_match: int  # 0-100
    title_match: int  # 0-100
    experience_match: int  # 0-100
    reasons: List[str] = field(default_factory=list)

    def get_emoji_rating(self) -> str:
        """Get star rating based on score."""
        if self.overall_score >= 90:
            return "⭐⭐⭐⭐⭐"
        elif self.overall_score >= 75:
            return "⭐⭐⭐⭐"
        elif self.overall_score >= 60:
            return "⭐⭐⭐"
        elif self.overall_score >= 40:
            return "⭐⭐"
        else:
            return "⭐"

    def get_fit_label(self) -> str:
        """Get human-readable fit label."""
        if self.overall_score >= 90:
            return "Excellent Match"
        elif self.overall_score >= 75:
            return "Strong Match"
        elif self.overall_score >= 60:
            return "Good Match"
        elif self.overall_score >= 40:
            return "Fair Match"
        else:
            return "Low Match"


class ResumeManager:
    """Manage resume storage and job matching."""

    RESUME_FILE = "resume_data.json"
    CURRENT_JOB_FILE = "current_job.json"

    # Common IT/Support skills to extract
    KNOWN_SKILLS = {
        # Technical
        "active directory", "windows", "macos", "linux", "office 365", "microsoft 365",
        "azure", "aws", "gcp", "google cloud", "servicenow", "jira", "zendesk",
        "freshdesk", "salesforce", "ticketing", "helpdesk", "desktop support",
        "network troubleshooting", "tcp/ip", "dns", "dhcp", "vpn", "wifi",
        "hardware troubleshooting", "printer support", "remote support",
        "powershell", "bash", "python", "sql", "scripting",
        "vmware", "citrix", "virtualization", "imaging", "deployment",
        "antivirus", "endpoint security", "cybersecurity", "mfa",
        "okta", "sso", "identity management", "intune", "jamf", "mdm",
        "itil", "itsm", "sla", "incident management", "change management",

        # Soft skills
        "customer service", "communication", "problem solving", "troubleshooting",
        "technical support", "documentation", "training", "leadership",
        "team management", "project management", "multitasking",

        # AI/Modern
        "ai", "artificial intelligence", "machine learning", "chatbot",
        "automation", "rpa", "chatgpt", "copilot", "generative ai",
    }

    # Job title patterns
    TITLE_PATTERNS = [
        r"(it\s+support\s+\w+)",
        r"(help\s+desk\s+\w+)",
        r"(desktop\s+support\s+\w+)",
        r"(technical\s+support\s+\w+)",
        r"(customer\s+support\s+\w+)",
        r"(service\s+desk\s+\w+)",
        r"(systems?\s+administrator)",
        r"(network\s+administrator)",
        r"(support\s+engineer)",
        r"(support\s+analyst)",
        r"(support\s+specialist)",
        r"(support\s+technician)",
        r"(support\s+lead)",
        r"(support\s+manager)",
    ]

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path(".")
        self.resume: Optional[Resume] = None
        self.current_job: Optional[CurrentJob] = None
        self._load_data()

    def _load_data(self):
        """Load saved resume and job data."""
        resume_path = self.data_dir / self.RESUME_FILE
        job_path = self.data_dir / self.CURRENT_JOB_FILE

        if resume_path.exists():
            try:
                with open(resume_path) as f:
                    data = json.load(f)
                    data['keywords'] = set(data.get('keywords', []))
                    self.resume = Resume(**data)
            except Exception as e:
                print(f"Error loading resume: {e}")

        if job_path.exists():
            try:
                with open(job_path) as f:
                    self.current_job = CurrentJob(**json.load(f))
            except Exception as e:
                print(f"Error loading current job: {e}")

    def _save_data(self):
        """Save resume and job data."""
        if self.resume:
            resume_path = self.data_dir / self.RESUME_FILE
            data = asdict(self.resume)
            data['keywords'] = list(data['keywords'])
            with open(resume_path, 'w') as f:
                json.dump(data, f, indent=2)

        if self.current_job:
            job_path = self.data_dir / self.CURRENT_JOB_FILE
            with open(job_path, 'w') as f:
                json.dump(asdict(self.current_job), f, indent=2)

    def update_resume(self, resume_text: str) -> Resume:
        """Parse and save a new resume."""
        self.resume = self._parse_resume(resume_text)
        self._save_data()
        return self.resume

    def update_resume_from_file(self, file_path: str) -> Resume:
        """Load resume from a text/PDF file."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Resume file not found: {file_path}")

        if path.suffix.lower() == '.pdf':
            text = self._extract_pdf_text(path)
        else:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

        return self.update_resume(text)

    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text from PDF file."""
        try:
            import PyPDF2
            text = ""
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except ImportError:
            # Fallback: try pdfplumber
            try:
                import pdfplumber
                text = ""
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                return text
            except ImportError:
                raise ImportError("Install PyPDF2 or pdfplumber to read PDF files: pip install PyPDF2")

    def _parse_resume(self, text: str) -> Resume:
        """Extract structured data from resume text."""
        text_lower = text.lower()

        # Extract skills
        skills = []
        for skill in self.KNOWN_SKILLS:
            if skill in text_lower:
                skills.append(skill)

        # Extract job titles from experience
        job_titles = []
        for pattern in self.TITLE_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            job_titles.extend([m.strip().title() for m in matches])
        job_titles = list(set(job_titles))

        # Estimate experience years
        year_patterns = [
            r"(\d+)\+?\s*years?\s+(?:of\s+)?experience",
            r"experience[:\s]+(\d+)\+?\s*years?",
            r"(\d+)\+?\s*years?\s+in\s+(?:it|tech|support)",
        ]
        experience_years = 0
        for pattern in year_patterns:
            match = re.search(pattern, text_lower)
            if match:
                experience_years = max(experience_years, int(match.group(1)))

        # Extract education
        education = []
        edu_patterns = [
            r"(bachelor'?s?\s+(?:of\s+)?(?:science|arts|engineering)\s*(?:in\s+[\w\s]+)?)",
            r"(associate'?s?\s+degree\s*(?:in\s+[\w\s]+)?)",
            r"(master'?s?\s+(?:of\s+)?(?:science|arts|business)\s*(?:in\s+[\w\s]+)?)",
            r"(b\.?s\.?\s+in\s+[\w\s]+)",
            r"(a\.?a\.?s?\.?\s+in\s+[\w\s]+)",
        ]
        for pattern in edu_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            education.extend([m.strip().title() for m in matches])

        # Extract certifications
        certifications = []
        cert_keywords = [
            "comptia a+", "comptia network+", "comptia security+",
            "comptia a\\+", "comptia network\\+", "comptia security\\+",
            "mcsa", "mcse", "mcp", "azure administrator", "aws certified",
            "google it support", "itil", "itil v4", "hdaa", "hdi",
            "ccna", "ccnp", "cissp", "cism",
        ]
        for cert in cert_keywords:
            if re.search(cert.replace("+", "\\+"), text_lower):
                certifications.append(cert.replace("\\+", "+").upper())

        # Build keyword set
        keywords = set()
        keywords.update(skills)
        keywords.update([t.lower() for t in job_titles])

        # Add additional contextual keywords
        for word in re.findall(r'\b[a-zA-Z]{3,}\b', text_lower):
            if word in self.KNOWN_SKILLS:
                keywords.add(word)

        return Resume(
            raw_text=text,
            skills=skills,
            job_titles=job_titles,
            experience_years=experience_years,
            education=education,
            certifications=list(set(certifications)),
            keywords=keywords,
            last_updated=datetime.now().isoformat(),
        )

    def update_current_job(self, title: str, description: str = "",
                          skills: List[str] = None, responsibilities: List[str] = None):
        """Set current job for comparison."""
        self.current_job = CurrentJob(
            title=title,
            description=description,
            skills=skills or [],
            responsibilities=responsibilities or [],
        )
        self._save_data()

    def calculate_fit_score(self, job_title: str, job_description: str = "",
                           job_location: str = "", job_company: str = "") -> JobFitScore:
        """Calculate how well a job matches the resume and current job."""
        if not self.resume:
            return JobFitScore(
                overall_score=50,
                skill_match=50,
                title_match=50,
                experience_match=50,
                reasons=["No resume uploaded - using default scoring"]
            )

        reasons = []
        job_title_lower = job_title.lower()
        job_desc_lower = job_description.lower() if job_description else ""
        combined_text = f"{job_title_lower} {job_desc_lower}"

        # === Skill Match (0-100) ===
        skill_matches = 0
        matched_skills = []

        for skill in self.resume.skills:
            if skill in combined_text:
                skill_matches += 1
                matched_skills.append(skill)

        if self.resume.skills:
            skill_match = min(100, int((skill_matches / len(self.resume.skills)) * 100) + 20)
        else:
            skill_match = 50

        if matched_skills:
            reasons.append(f"Skills: {', '.join(matched_skills[:3])}")

        # === Title Match (0-100) ===
        title_match = 40  # Base score

        # Check against resume job titles
        for resume_title in self.resume.job_titles:
            if resume_title.lower() in job_title_lower:
                title_match = 90
                reasons.append(f"Title matches experience: {resume_title}")
                break

        # Check against current job if set
        if self.current_job and self.current_job.title:
            current_title_lower = self.current_job.title.lower()

            # Check for progression (lead, senior, manager from current role)
            progression_keywords = ["lead", "senior", "manager", "ii", "iii", "principal"]
            is_progression = any(kw in job_title_lower for kw in progression_keywords)

            # Same field?
            common_terms = ["support", "help desk", "it ", "technical", "customer", "service"]
            same_field = any(term in current_title_lower and term in job_title_lower for term in common_terms)

            if same_field:
                title_match = max(title_match, 70)
                if is_progression:
                    title_match = 95
                    reasons.append("Career progression opportunity")

        # Keywords in title
        title_keywords = ["it support", "help desk", "technical support", "desktop support",
                         "service desk", "customer experience", "ai support", "support lead"]
        for kw in title_keywords:
            if kw in job_title_lower:
                title_match = max(title_match, 75)
                break

        # === Experience Match (0-100) ===
        experience_match = 60  # Default

        # Check for experience requirements in description
        exp_patterns = [
            r"(\d+)\+?\s*years?\s+(?:of\s+)?experience",
            r"minimum\s+(\d+)\s+years?",
            r"at\s+least\s+(\d+)\s+years?",
        ]

        required_years = 0
        for pattern in exp_patterns:
            match = re.search(pattern, combined_text)
            if match:
                required_years = max(required_years, int(match.group(1)))

        if required_years > 0:
            if self.resume.experience_years >= required_years:
                experience_match = 100
                reasons.append(f"Experience: {self.resume.experience_years}+ yrs (need {required_years})")
            elif self.resume.experience_years >= required_years - 1:
                experience_match = 75
                reasons.append(f"Experience close: {self.resume.experience_years} yrs (need {required_years})")
            else:
                experience_match = max(30, 60 - (required_years - self.resume.experience_years) * 10)
        else:
            # No explicit requirement - assume entry-mid level
            if self.resume.experience_years >= 2:
                experience_match = 85

        # Certification boost
        if self.resume.certifications:
            cert_text = " ".join(self.resume.certifications).lower()
            if any(cert.lower() in combined_text for cert in self.resume.certifications):
                experience_match = min(100, experience_match + 15)
                reasons.append("Certification match")

        # === Calculate Overall Score ===
        # Weighted average
        overall_score = int(
            skill_match * 0.35 +      # Skills most important
            title_match * 0.40 +       # Title relevance crucial
            experience_match * 0.25    # Experience matters
        )

        # Bonus for exact matches
        if skill_match >= 80 and title_match >= 80:
            overall_score = min(100, overall_score + 10)
            reasons.append("Strong overall fit")

        return JobFitScore(
            overall_score=overall_score,
            skill_match=skill_match,
            title_match=title_match,
            experience_match=experience_match,
            reasons=reasons,
        )

    def has_resume(self) -> bool:
        """Check if a resume is loaded."""
        return self.resume is not None

    def get_resume_summary(self) -> str:
        """Get a summary of the loaded resume."""
        if not self.resume:
            return "No resume loaded"

        return (
            f"Skills: {len(self.resume.skills)}\n"
            f"Experience: {self.resume.experience_years}+ years\n"
            f"Certifications: {len(self.resume.certifications)}\n"
            f"Last updated: {self.resume.last_updated[:10] if self.resume.last_updated else 'Unknown'}"
        )


# Global instance
resume_manager = ResumeManager()


if __name__ == "__main__":
    # Test with sample resume
    sample_resume = """
    IT Support Specialist with 5+ years of experience in desktop support and help desk operations.

    Skills:
    - Active Directory, Windows, macOS, Linux
    - Office 365, Azure, ServiceNow, Jira
    - Network troubleshooting, TCP/IP, DNS, DHCP, VPN
    - Remote support, hardware troubleshooting
    - Customer service, documentation, training

    Certifications:
    - CompTIA A+
    - CompTIA Network+
    - ITIL v4 Foundation

    Education:
    - Bachelor's of Science in Information Technology
    """

    manager = ResumeManager()
    resume = manager.update_resume(sample_resume)

    print("Parsed Resume:")
    print(f"  Skills: {resume.skills}")
    print(f"  Experience: {resume.experience_years} years")
    print(f"  Certifications: {resume.certifications}")
    print(f"  Keywords: {len(resume.keywords)}")

    # Test fit scoring
    score = manager.calculate_fit_score(
        "IT Support Specialist II",
        "Looking for 3+ years experience in desktop support, Active Directory, Office 365"
    )
    print(f"\nFit Score: {score.overall_score}/100 ({score.get_fit_label()})")
    print(f"  {score.get_emoji_rating()}")
    print(f"  Reasons: {score.reasons}")
