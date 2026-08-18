"""
Evaluation dataset creation and management for RAG system
Uses unified 'ground_truth' field name (RAGAS standard)
"""

import json
import random
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .config import GROUND_TRUTH_PATH, TEST_QUERIES_PATH, QUERY_CATEGORIES
from config.paths import PathConfig

# Course codes verified present in the scraped knowledge base (checked
# against PathConfig.SCRAPED_CONTENT_FILES_DIR during the fallback-rate
# investigation, SPEC.md). Do NOT add a code here without confirming a
# matching *_2025_<CODE>.json file actually exists -- the previous
# hand-written ground truth asked about COMP1521, COMP3331, and
# MATH1081/1131/1231, none of which exist in this deployment's scraped
# handbook data. Those questions were unanswerable by construction: no
# amount of pipeline tuning fixes a query about a document that was never
# retrieved because it was never scraped.
VERIFIED_COURSE_CODES = [
    "COMP1511", "COMP1531", "COMP2511", "COMP2521", "COMP3121",
    "COMP3311", "COMP6441", "COMP9900", "COMP3411", "COMP6080",
    "COMP3900", "COMP2041", "COMP3231",
]

# code -> UNSW program name, verified present the same way.
VERIFIED_PROGRAM_CODES = {
    "3778": "Bachelor of Computer Science",
    "8543": "Master of Information Technology",
    "3777": "Bachelor of Cyber Security",
    "3782": "Bachelor of Advanced Science (Honours) / Computer Science",
}

# Facts manually verified against the actual PDF text in
# data/knowledge_base/documents/ (extracted via pypdf during the
# fallback-rate investigation, SPEC.md) rather than written from general
# knowledge about UNSW -- these are the only source documents this
# category can draw on, so the ground_truth has to match what's actually
# in them, not what's generically true about the university.
PDF_GROUND_TRUTH = [
    {
        "question": "What CSE-related societies exist at UNSW?",
        "ground_truth": "UNSW hosts several student-run societies relevant to Computer Science and Engineering students, offering technical projects, social events, mentorship, and professional development opportunities.",
        "category": "campus_facilities",
        "difficulty": "easy",
        "expected_context_keywords": ["society", "CSE", "students", "club"],
        "source_pdf": "CSE_Societies.pdf",
    },
    {
        "question": "What mental health support is available for UNSW students?",
        "ground_truth": "UNSW offers Mental Health Connect, a service to help students find the mental health support they need, including links for urgent 24/7 confidential help.",
        "category": "campus_facilities",
        "difficulty": "easy",
        "expected_context_keywords": ["mental health", "support", "UNSW", "students"],
        "source_pdf": "Mental_Health_Support___UNSW_Current_Students.pdf",
    },
    {
        "question": "What is the graduate employment rate for UNSW CSE?",
        "ground_truth": "According to the 2024 Graduate Outcomes Survey, over 90% of UNSW CSE graduates secure full-time employment within 4 to 6 months of graduation.",
        "category": "campus_facilities",
        "difficulty": "easy",
        "expected_context_keywords": ["employment", "graduate", "CSE", "90%"],
        "source_pdf": "UNSW_CSE_Employment_Rate.pdf",
    },
    {
        "question": "Where are the CSE computer labs located?",
        "ground_truth": "UNSW CSE operates teaching and project laboratories across several buildings on the Kensington campus, including labs in the K17 building, for undergraduate and postgraduate learning, project development, and research.",
        "category": "campus_facilities",
        "difficulty": "easy",
        "expected_context_keywords": ["labs", "K17", "Kensington", "computer"],
        "source_pdf": "UNSW_CSE_Labs.pdf",
    },
    {
        "question": "What accommodation options does UNSW offer?",
        "ground_truth": "UNSW provides on-campus housing broadly divided into University Colleges and Independent Apartments, catering to undergraduate, postgraduate, and international students.",
        "category": "campus_facilities",
        "difficulty": "easy",
        "expected_context_keywords": ["accommodation", "colleges", "apartments", "housing"],
        "source_pdf": "UNSW_Campus_Accommodation_Overview_2025.pdf",
    },
    {
        "question": "What is the ATAR requirement for the Bachelor of Computer Science?",
        "ground_truth": "The Bachelor of Computer Science (3778) at UNSW typically requires an ATAR around 92.0 (adjusted) for domestic students, with Mathematics Extension 1 or 2 strongly recommended as assumed knowledge.",
        "category": "admission_requirements",
        "difficulty": "medium",
        "expected_context_keywords": ["ATAR", "92", "Computer Science", "3778"],
        "source_pdf": "UNSW_Entry_Requirements_2025.pdf",
    },
    {
        "question": "What industry partnership opportunities does UNSW CSE offer?",
        "ground_truth": "UNSW CSE operates a tiered Industry Partnership Program (Silver, Gold, Platinum) linking companies with the School's research, talent, and events, including involvement in student capstone projects and networking events.",
        "category": "general_inquiries",
        "difficulty": "medium",
        "expected_context_keywords": ["industry", "partnership", "capstone", "CSE"],
        "source_pdf": "UNSW_Industry_Partnership.pdf",
    },
    {
        "question": "Where can I study on campus at UNSW?",
        "ground_truth": "UNSW has study spaces across campus including Morven Brown (C20) with 134 seats and Wallace Wurth (C27) with 196 seats, offering facilities such as 24/7 access, power outlets, and group workspaces.",
        "category": "campus_facilities",
        "difficulty": "easy",
        "expected_context_keywords": ["study spaces", "Morven Brown", "Wallace Wurth", "campus"],
        "source_pdf": "UNSW_Study_Spaces_1.pdf",
    },
    {
        "question": "Where can I park as a visitor at UNSW?",
        "ground_truth": "Limited visitor parking is available at the Kensington campus, including the Botany Street Multi-storey Car Park (via Gate 11) and the Barker Street Multi-storey Car Park (via Gate 14), paid via pay-by-plate meters or the CellOPark app.",
        "category": "campus_facilities",
        "difficulty": "easy",
        "expected_context_keywords": ["parking", "visitor", "car park", "Kensington"],
        "source_pdf": "Visitor_Parking.pdf",
    },
    {
        "question": "Are there scholarships for international students at UNSW?",
        "ground_truth": "UNSW offers a range of scholarships for international students who want to experience university life in Australia, rewarding their ambition to study at UNSW.",
        "category": "admission_requirements",
        "difficulty": "easy",
        "expected_context_keywords": ["scholarship", "international", "students"],
        "source_pdf": "Scholarships_for_international_students___UNSW_Sydney.pdf",
    },
]

# Queries the knowledge base has no source document for at all -- not
# malicious or off-topic in the safety_checker.py sense, just genuinely
# outside what a UNSW CSE handbook/facilities corpus covers. The pipeline
# is expected to decline gracefully (fallback_used=True) rather than
# fabricate an answer. These don't get a ground_truth or RAGAS scoring --
# there is no "correct grounded answer" to compare against, the correct
# behavior IS the fallback.
OUT_OF_SCOPE_QUERIES = [
    {
        "query": "What's the weather forecast for Sydney this week?",
        "category": "out_of_scope",
        "difficulty": "easy",
        "expected_behavior": "fallback",
    },
    {
        "query": "Can you help me debug my Python homework for a course at MIT?",
        "category": "out_of_scope",
        "difficulty": "easy",
        "expected_behavior": "fallback",
    },
    {
        "query": "What is the meal plan at Stanford University's dining halls?",
        "category": "out_of_scope",
        "difficulty": "easy",
        "expected_behavior": "fallback",
    },
    {
        "query": "What are the admission requirements for UNSW Medicine?",
        "category": "out_of_scope",
        "difficulty": "medium",
        "expected_behavior": "fallback",
    },
    {
        "query": "Can I transfer credit from another university into UNSW Computer Science?",
        "category": "out_of_scope",
        "difficulty": "medium",
        "expected_behavior": "fallback",
    },
]

# Navigation-intent queries -- these should be classified NAVIGATION by
# safety_and_rewrite_node and routed straight to fallback_node's MazeMap
# guidance without ever attempting RAG retrieval (see graph_rag.py
# route_after_safety_and_rewrite). expected_behavior="navigation" checks
# performance.query_intent directly rather than inferring it.
NAVIGATION_QUERIES = [
    {"query": "Where is J17?", "category": "navigation", "difficulty": "easy", "expected_behavior": "navigation"},
    {"query": "How do I get to the CSE building?", "category": "navigation", "difficulty": "easy", "expected_behavior": "navigation"},
    {"query": "Where is K17 located on campus?", "category": "navigation", "difficulty": "easy", "expected_behavior": "navigation"},
    {"query": "Show me the location of the main library", "category": "navigation", "difficulty": "easy", "expected_behavior": "navigation"},
]


def _load_scraped_page(code: str) -> Optional[Dict]:
    """Find and load the scraped handbook JSON for a course/program code, if present."""
    content_dir = PathConfig.SCRAPED_CONTENT_FILES_DIR
    if not content_dir.exists():
        return None
    matches = list(content_dir.glob(f"*_2025_{code}.json"))
    if not matches:
        return None
    with open(matches[0], encoding='utf-8') as f:
        return json.load(f)


def _extract_overview(page_content: str, max_chars: int = 350) -> str:
    """Pull the real 'Overview' section out of a scraped handbook page's raw text."""
    match = re.search(r'## Overview\n(.*?)\n## ', page_content, re.S)
    if not match:
        return ""
    text = match.group(1)
    text = text.replace('Â', '')  # scraper mojibake artifact around non-breaking spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_chars]


class EvaluationDataset:
    """Manages evaluation datasets for RAG testing"""

    def __init__(self):
        self.ground_truth = []
        self.test_queries = []

    def create_unsw_ground_truth(self) -> List[Dict[str, Any]]:
        """
        Build ground truth from content verified present in the knowledge
        base at generation time (course/program pages, see
        VERIFIED_COURSE_CODES/VERIFIED_PROGRAM_CODES) plus manually
        fact-checked PDF summaries (PDF_GROUND_TRUTH), instead of the
        previous hand-written facts that had no guarantee of a matching
        source document at all.

        Courses/programs not found in the knowledge base at generation
        time (e.g. the corpus was re-scraped and a course was dropped)
        are skipped with a warning rather than silently producing an
        unanswerable ground truth entry again.
        """
        ground_truth_data = []

        for code in VERIFIED_COURSE_CODES:
            page = _load_scraped_page(code)
            if not page:
                print(f"[EvaluationDataset] Skipping {code}: no longer found in knowledge base")
                continue
            title = page.get("metadata", {}).get("title", code)
            overview = _extract_overview(page.get("page_content", ""))
            if not overview:
                print(f"[EvaluationDataset] Skipping {code}: no Overview section found")
                continue
            ground_truth_data.append({
                "question": f"What is {code}?",
                "ground_truth": f"{code} ({title}). {overview}",
                "category": "course_information",
                "difficulty": "easy",
                "expected_context_keywords": [code, title],
            })

        for code, name in VERIFIED_PROGRAM_CODES.items():
            page = _load_scraped_page(code)
            if not page:
                print(f"[EvaluationDataset] Skipping program {code}: no longer found in knowledge base")
                continue
            overview = _extract_overview(page.get("page_content", ""))
            if not overview:
                print(f"[EvaluationDataset] Skipping program {code}: no Overview section found")
                continue
            ground_truth_data.append({
                "question": f"What is the {name}?",
                "ground_truth": f"The {name} ({code}) at UNSW. {overview}",
                "category": "degree_programs",
                "difficulty": "medium",
                "expected_context_keywords": [code, name],
            })

        for item in PDF_GROUND_TRUTH:
            entry = {k: v for k, v in item.items() if k != "source_pdf"}
            ground_truth_data.append(entry)

        # Add metadata
        for item in ground_truth_data:
            item.update({
                "created_at": datetime.now().isoformat(),
                "source": "verified_knowledge_base",
                "version": "3.0"
            })

        self.ground_truth = ground_truth_data
        return ground_truth_data

    def generate_test_queries(self, sample_size: int = 50) -> List[Dict[str, Any]]:
        """
        Generate diverse test queries for evaluation: direct + rephrased
        questions drawn from verified ground truth, plus a fixed set of
        out-of-scope queries (system should fallback rather than
        hallucinate) and navigation queries (system should classify
        NAVIGATION and never attempt RAG retrieval at all). The latter two
        categories are always included in full (not counted against
        sample_size's random sampling) since they're specifically there to
        test those two behaviors, not to be RAGAS-scored -- see
        evaluation/pipeline.py's handling of expected_behavior.
        """

        if not self.ground_truth:
            self.create_unsw_ground_truth()

        # Create test queries from ground truth
        scored_queries = []

        for gt in self.ground_truth:
            # Original question as a test query
            scored_queries.append({
                "query": gt["question"],
                "ground_truth": gt["ground_truth"],
                "category": gt["category"],
                "difficulty": gt["difficulty"],
                "query_type": "direct",
                "expected_context_keywords": gt["expected_context_keywords"]
            })

            # Create rephrased variations
            variations = self._create_query_variations(gt)
            scored_queries.extend(variations)

        behavioral_queries = list(OUT_OF_SCOPE_QUERIES) + list(NAVIGATION_QUERIES)

        # Limit the RAGAS-scored portion to the requested sample size;
        # behavioral checks are cheap (no RAGAS LLM-judge calls) and always
        # run in full so navigation/fallback correctness gets checked every
        # run regardless of how small a sample_size was requested.
        if len(scored_queries) > sample_size:
            random.seed(42)
            scored_queries = random.sample(scored_queries, sample_size)

        test_queries = scored_queries + behavioral_queries

        # Add metadata
        for i, query in enumerate(test_queries):
            query.update({
                "id": f"query_{i:03d}",
                "created_at": datetime.now().isoformat(),
                "version": "3.0"
            })

        self.test_queries = test_queries
        return test_queries

    def _create_query_variations(self, ground_truth_item: Dict) -> List[Dict]:
        """Create variations of a ground truth question"""
        variations = []
        base_question = ground_truth_item["question"]

        # Simple rephrasing patterns
        if "What is" in base_question:
            course_code = self._extract_course_code(base_question)
            if course_code:
                variations.append({
                    "query": f"Tell me about {course_code}",
                    "ground_truth": ground_truth_item["ground_truth"],
                    "category": ground_truth_item["category"],
                    "difficulty": ground_truth_item["difficulty"],
                    "query_type": "rephrased",
                    "expected_context_keywords": ground_truth_item["expected_context_keywords"]
                })

        return variations

    def _extract_course_code(self, question: str) -> Optional[str]:
        """Extract course code from question if present"""
        import re
        match = re.search(r'COMP\d{4}', question)
        return match.group(0) if match else None

    def save_datasets(self):
        """Save ground truth and test queries to files"""
        if not self.ground_truth:
            self.create_unsw_ground_truth()

        if not self.test_queries:
            self.generate_test_queries()

        # Save ground truth
        with open(GROUND_TRUTH_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.ground_truth, f, indent=2, ensure_ascii=False)

        # Save test queries
        with open(TEST_QUERIES_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.test_queries, f, indent=2, ensure_ascii=False)

        print(f"Saved {len(self.ground_truth)} ground truth items to {GROUND_TRUTH_PATH}")
        print(f"Saved {len(self.test_queries)} test queries to {TEST_QUERIES_PATH}")

    def load_datasets(self):
        """Load datasets from files"""
        try:
            if GROUND_TRUTH_PATH.exists():
                with open(GROUND_TRUTH_PATH, 'r', encoding='utf-8') as f:
                    self.ground_truth = json.load(f)

            if TEST_QUERIES_PATH.exists():
                with open(TEST_QUERIES_PATH, 'r', encoding='utf-8') as f:
                    self.test_queries = json.load(f)

        except Exception as e:
            print(f"Error loading datasets: {e}")

    def get_queries_by_category(self, category: str) -> List[Dict]:
        """Get test queries filtered by category"""
        if not self.test_queries:
            self.load_datasets()

        return [q for q in self.test_queries if q.get('category') == category]

    def get_queries_by_difficulty(self, difficulty: str) -> List[Dict]:
        """Get test queries filtered by difficulty"""
        if not self.test_queries:
            self.load_datasets()

        return [q for q in self.test_queries if q.get('difficulty') == difficulty]
