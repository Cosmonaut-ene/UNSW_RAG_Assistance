"""
Evaluation dataset creation and management for RAG system
Uses unified 'ground_truth' field name (RAGAS standard)
"""

import json
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .config import GROUND_TRUTH_PATH, TEST_QUERIES_PATH, QUERY_CATEGORIES


class EvaluationDataset:
    """Manages evaluation datasets for RAG testing"""

    def __init__(self):
        self.ground_truth = []
        self.test_queries = []

    def create_unsw_ground_truth(self) -> List[Dict[str, Any]]:
        """Create ground truth dataset with UNSW-specific questions and answers.
        All entries use 'ground_truth' as the standard field name."""

        ground_truth_data = [
            # ===== Course Information (~30%) =====
            {
                "question": "What is COMP1511?",
                "ground_truth": "COMP1511 Programming Fundamentals is an introductory course that teaches programming in C. It covers basic programming concepts including variables, control flow, functions, arrays, strings, and pointers. It is typically taken in the first term of a Computer Science degree at UNSW.",
                "category": "course_information",
                "difficulty": "easy",
                "expected_context_keywords": ["COMP1511", "Programming Fundamentals", "C", "introductory"]
            },
            {
                "question": "What is COMP1521?",
                "ground_truth": "COMP1521 Computer Systems Fundamentals covers how programs execute on computer hardware. Topics include data representation, machine-level programming (MIPS assembly), memory hierarchy, caching, virtual memory, file systems, and concurrency. It builds on COMP1511.",
                "category": "course_information",
                "difficulty": "easy",
                "expected_context_keywords": ["COMP1521", "Computer Systems", "assembly", "memory"]
            },
            {
                "question": "What is COMP2521?",
                "ground_truth": "COMP2521 Data Structures and Algorithms teaches fundamental data structures such as linked lists, binary search trees, balanced trees, heaps, graphs and hash tables. It covers sorting algorithms, graph algorithms, and algorithmic complexity analysis. It is a core second-year course.",
                "category": "course_information",
                "difficulty": "easy",
                "expected_context_keywords": ["COMP2521", "Data Structures", "Algorithms", "trees", "graphs"]
            },
            {
                "question": "What is COMP2511?",
                "ground_truth": "COMP2511 Object-Oriented Design and Programming teaches object-oriented principles using Java. Topics include design patterns, UML modelling, inheritance, polymorphism, interfaces, generics, and software design principles like SOLID.",
                "category": "course_information",
                "difficulty": "easy",
                "expected_context_keywords": ["COMP2511", "Object-Oriented", "Java", "design patterns"]
            },
            {
                "question": "What is COMP3311?",
                "ground_truth": "COMP3311 Database Systems covers the design, implementation, and use of relational database management systems. Topics include ER modelling, SQL, relational algebra, normalisation, query processing, and transaction management. It uses PostgreSQL.",
                "category": "course_information",
                "difficulty": "easy",
                "expected_context_keywords": ["COMP3311", "Database", "SQL", "relational", "PostgreSQL"]
            },
            {
                "question": "What is COMP3331?",
                "ground_truth": "COMP3331 Computer Networks and Applications introduces the fundamentals of computer networking. Topics include the Internet architecture, application layer protocols (HTTP, DNS, SMTP), transport layer (TCP, UDP), network layer (IP, routing), and link layer protocols.",
                "category": "course_information",
                "difficulty": "easy",
                "expected_context_keywords": ["COMP3331", "Networks", "TCP", "IP", "protocols"]
            },
            {
                "question": "What is COMP9900?",
                "ground_truth": "COMP9900 is a capstone project course where students work in teams to develop a substantial software project over a term. It involves project management, software engineering practices, regular demonstrations, and a final presentation. It is typically taken in the final year.",
                "category": "course_information",
                "difficulty": "easy",
                "expected_context_keywords": ["COMP9900", "capstone", "project", "team", "software"]
            },
            {
                "question": "What programming languages are taught in first year?",
                "ground_truth": "First-year Computer Science students at UNSW primarily learn C in COMP1511 (Programming Fundamentals) and continue with C and MIPS assembly in COMP1521 (Computer Systems Fundamentals). Some courses may also introduce Python or other languages depending on the electives chosen.",
                "category": "course_information",
                "difficulty": "medium",
                "expected_context_keywords": ["C", "COMP1511", "COMP1521", "programming", "first year"]
            },
            {
                "question": "What is COMP6441?",
                "ground_truth": "COMP6441 Security Engineering and Cyber Security covers the principles and practice of computer security. Topics include cryptography, authentication, access control, network security, web security, and security analysis techniques.",
                "category": "course_information",
                "difficulty": "medium",
                "expected_context_keywords": ["COMP6441", "Security", "cyber", "cryptography"]
            },
            {
                "question": "What is COMP3121?",
                "ground_truth": "COMP3121 Algorithm Design and Analysis is an advanced algorithms course covering algorithm design techniques such as divide and conquer, dynamic programming, greedy algorithms, network flow, and NP-completeness. It builds upon COMP2521.",
                "category": "course_information",
                "difficulty": "medium",
                "expected_context_keywords": ["COMP3121", "Algorithm", "dynamic programming", "NP"]
            },
            {
                "question": "What topics are covered in COMP9900?",
                "ground_truth": "COMP9900 covers software engineering methodology, agile project management, team collaboration, requirements analysis, system design, implementation, testing, and project presentation skills. Students work in teams of 4-5 to build a real software product.",
                "category": "course_information",
                "difficulty": "medium",
                "expected_context_keywords": ["COMP9900", "agile", "team", "software engineering", "project"]
            },
            {
                "question": "What is MATH1081?",
                "ground_truth": "MATH1081 Discrete Mathematics covers mathematical foundations for computer science including sets, logic, proof techniques, counting and combinatorics, graph theory, and number theory. It is a core first-year requirement for CS students.",
                "category": "course_information",
                "difficulty": "easy",
                "expected_context_keywords": ["MATH1081", "Discrete Mathematics", "logic", "graph theory"]
            },
            {
                "question": "What is artificial intelligence at UNSW CSE?",
                "ground_truth": "UNSW CSE offers artificial intelligence courses including COMP3411 Artificial Intelligence which covers search algorithms, game playing, knowledge representation, machine learning basics, and natural language processing. COMP9444 Neural Networks and Deep Learning covers modern deep learning techniques.",
                "category": "course_information",
                "difficulty": "medium",
                "expected_context_keywords": ["artificial intelligence", "COMP3411", "machine learning", "deep learning"]
            },
            {
                "question": "What web development courses are available?",
                "ground_truth": "UNSW CSE offers COMP6080 Web Front-End Programming which covers modern web development using HTML, CSS, JavaScript, and frameworks like React. COMP3900/COMP9900 also involves significant web development as part of the capstone project.",
                "category": "course_information",
                "difficulty": "medium",
                "expected_context_keywords": ["web development", "COMP6080", "JavaScript", "React"]
            },
            {
                "question": "What is software testing at UNSW?",
                "ground_truth": "COMP3153 Algorithmic Verification and SENG2021 Software Engineering Workshops cover aspects of software testing. Additionally, testing practices are integrated into courses like COMP2511, COMP1531, and COMP9900 where students are expected to write unit tests and integration tests.",
                "category": "course_information",
                "difficulty": "hard",
                "expected_context_keywords": ["testing", "software", "SENG", "unit tests"]
            },

            # ===== Degree Programs (~20%) =====
            {
                "question": "What is the Bachelor of Computer Science?",
                "ground_truth": "The Bachelor of Computer Science (3778) at UNSW is a 3-year full-time undergraduate degree. Students complete 144 units of credit (UOC) including core computing courses, mathematics, and electives. It offers specialisations in areas like Artificial Intelligence, Database Systems, and Security Engineering.",
                "category": "degree_programs",
                "difficulty": "easy",
                "expected_context_keywords": ["Bachelor", "Computer Science", "3-year", "144", "UOC"]
            },
            {
                "question": "How long is the Computer Science degree?",
                "ground_truth": "The Bachelor of Computer Science at UNSW is a 3-year full-time degree requiring 144 units of credit (UOC). Part-time study is available and typically takes up to 6 years. Students take approximately 8 courses per year (4 per term).",
                "category": "degree_programs",
                "difficulty": "easy",
                "expected_context_keywords": ["3-year", "144 units", "UOC", "full-time", "part-time"]
            },
            {
                "question": "What is the Master of Information Technology?",
                "ground_truth": "The Master of Information Technology (MIT, program 8543) is a 2-year postgraduate degree at UNSW for students from non-computing backgrounds who want to transition into IT. It covers programming, databases, web development, software engineering, and includes a capstone project.",
                "category": "degree_programs",
                "difficulty": "medium",
                "expected_context_keywords": ["Master", "Information Technology", "MIT", "2-year", "postgraduate"]
            },
            {
                "question": "Can I do a double degree with Computer Science?",
                "ground_truth": "Yes, UNSW offers several double degree options with Computer Science including Computer Science/Commerce, Computer Science/Mathematics, Computer Science/Science, and Computer Science/Arts. Double degrees typically take 4-5 years full-time.",
                "category": "degree_programs",
                "difficulty": "medium",
                "expected_context_keywords": ["double degree", "Commerce", "Mathematics", "4-5 years"]
            },
            {
                "question": "What is the Bachelor of Software Engineering?",
                "ground_truth": "The Bachelor of Software Engineering (Honours) at UNSW (3707) is a 4-year degree that combines computer science fundamentals with engineering principles. It is accredited by Engineers Australia and includes core engineering courses, software project management, and a thesis project.",
                "category": "degree_programs",
                "difficulty": "medium",
                "expected_context_keywords": ["Software Engineering", "4-year", "Honours", "Engineers Australia"]
            },
            {
                "question": "What specialisations are available in Computer Science?",
                "ground_truth": "The Bachelor of Computer Science at UNSW offers specialisations including Artificial Intelligence, Computer Networks, Database Systems, Embedded Systems, Programming Languages, Security Engineering, and Theoretical Computer Science. Students choose one specialisation to complete.",
                "category": "degree_programs",
                "difficulty": "medium",
                "expected_context_keywords": ["specialisation", "Artificial Intelligence", "Security", "Database"]
            },
            {
                "question": "What is the Honours program in Computer Science?",
                "ground_truth": "Computer Science Honours at UNSW is an additional year of study (4th year) for high-achieving students. It involves a substantial research thesis supervised by an academic, plus advanced coursework. Entry typically requires a strong WAM (usually 65+). It provides pathways to PhD research.",
                "category": "degree_programs",
                "difficulty": "hard",
                "expected_context_keywords": ["Honours", "thesis", "research", "WAM", "4th year"]
            },
            {
                "question": "Are there part-time study options?",
                "ground_truth": "Yes, UNSW offers part-time study options for most Computer Science programs. Part-time students typically take 2-3 courses per term instead of 4. The Bachelor of Computer Science can take up to 6 years part-time. Postgraduate programs also offer part-time options.",
                "category": "degree_programs",
                "difficulty": "easy",
                "expected_context_keywords": ["part-time", "2-3 courses", "flexible"]
            },
            {
                "question": "What is the difference between CS and Software Engineering?",
                "ground_truth": "Computer Science (3 years) focuses on theoretical foundations and has more elective flexibility. Software Engineering (4 years with Honours) is engineering-accredited, includes professional engineering courses, a thesis, and more structured core requirements. Both cover programming and software development.",
                "category": "degree_programs",
                "difficulty": "hard",
                "expected_context_keywords": ["Computer Science", "Software Engineering", "3 years", "4 years", "accredited"]
            },
            {
                "question": "What is the co-op program?",
                "ground_truth": "The UNSW Co-op Program offers scholarships that combine academic study with industry placements. For Computer Science and Engineering, students complete multiple industry placements during their degree. Benefits include a scholarship stipend, guaranteed work experience, and industry mentoring.",
                "category": "degree_programs",
                "difficulty": "medium",
                "expected_context_keywords": ["co-op", "scholarship", "industry placement", "work experience"]
            },

            # ===== Prerequisites (~20%) =====
            {
                "question": "What are the prerequisites for COMP9900?",
                "ground_truth": "COMP9900 requires completion of at least 102 units of credit (UOC) and COMP2511 (Object-Oriented Design & Programming). Students must have sufficient programming experience and be in the later stages of their degree.",
                "category": "prerequisites",
                "difficulty": "medium",
                "expected_context_keywords": ["COMP9900", "102 UOC", "COMP2511", "prerequisites"]
            },
            {
                "question": "What are the prerequisites for COMP2521?",
                "ground_truth": "COMP2521 Data Structures and Algorithms requires COMP1511 (Programming Fundamentals) or DPST1091 or equivalent programming experience. Students should be comfortable with C programming before taking this course.",
                "category": "prerequisites",
                "difficulty": "medium",
                "expected_context_keywords": ["COMP2521", "COMP1511", "prerequisites", "programming"]
            },
            {
                "question": "Do I need COMP1511 before COMP2511?",
                "ground_truth": "Yes, COMP2511 requires COMP1531 (Software Engineering Fundamentals) as a prerequisite, which itself requires COMP1511. So you need COMP1511 -> COMP1531 -> COMP2511 as the standard progression. COMP2521 is also typically required or co-requisite.",
                "category": "prerequisites",
                "difficulty": "medium",
                "expected_context_keywords": ["COMP1511", "COMP1531", "COMP2511", "prerequisite"]
            },
            {
                "question": "What math subjects are required for Computer Science?",
                "ground_truth": "Computer Science students at UNSW typically need MATH1081 (Discrete Mathematics), MATH1131 or MATH1141 (Mathematics 1A), and MATH1231 or MATH1241 (Mathematics 1B). Additional math electives may be required depending on the specialisation.",
                "category": "prerequisites",
                "difficulty": "medium",
                "expected_context_keywords": ["MATH1081", "MATH1131", "MATH1231", "mathematics", "discrete"]
            },
            {
                "question": "Can I take COMP3311 without COMP2521?",
                "ground_truth": "COMP3311 Database Systems requires COMP2521 (Data Structures and Algorithms) as a prerequisite. Students need to complete COMP2521 before enrolling in COMP3311 to ensure they have the necessary algorithmic foundations.",
                "category": "prerequisites",
                "difficulty": "medium",
                "expected_context_keywords": ["COMP3311", "COMP2521", "prerequisite", "database"]
            },
            {
                "question": "What subjects should I complete in first year?",
                "ground_truth": "First-year Computer Science students should complete COMP1511 (Programming Fundamentals), COMP1521 (Computer Systems Fundamentals), COMP1531 (Software Engineering Fundamentals), MATH1081 (Discrete Mathematics), and MATH1131/MATH1231 (Mathematics 1A/1B).",
                "category": "prerequisites",
                "difficulty": "medium",
                "expected_context_keywords": ["COMP1511", "COMP1521", "COMP1531", "MATH1081", "first year"]
            },
            {
                "question": "What are the prerequisites for COMP3331?",
                "ground_truth": "COMP3331 Computer Networks requires COMP2521 (Data Structures and Algorithms) as a prerequisite. Students should have solid programming skills and understanding of data structures before studying networking.",
                "category": "prerequisites",
                "difficulty": "medium",
                "expected_context_keywords": ["COMP3331", "COMP2521", "prerequisite", "networks"]
            },
            {
                "question": "What subjects do I need for second year CS?",
                "ground_truth": "Second-year Computer Science courses include COMP2521 (Data Structures and Algorithms), COMP2511 (Object-Oriented Design), COMP1531 (Software Engineering Fundamentals if not taken in first year), and MATH electives. Prerequisites from first year must be completed.",
                "category": "prerequisites",
                "difficulty": "medium",
                "expected_context_keywords": ["second year", "COMP2521", "COMP2511", "COMP1531"]
            },
            {
                "question": "Are there entry requirements for postgraduate CS?",
                "ground_truth": "Postgraduate Computer Science programs at UNSW require a completed undergraduate degree. The Master of IT accepts graduates from any discipline. The Master of Computer Science typically requires a CS-related undergraduate degree with a minimum GPA/WAM. English language requirements (IELTS 6.5+) apply for international students.",
                "category": "prerequisites",
                "difficulty": "hard",
                "expected_context_keywords": ["postgraduate", "undergraduate degree", "GPA", "WAM", "IELTS"]
            },
            {
                "question": "How many units do I need to graduate?",
                "ground_truth": "The Bachelor of Computer Science requires 144 units of credit (UOC) to graduate. Most courses are worth 6 UOC, so students typically complete 24 courses over 3 years. Software Engineering requires 192 UOC over 4 years.",
                "category": "prerequisites",
                "difficulty": "easy",
                "expected_context_keywords": ["144", "UOC", "units", "graduate", "24 courses"]
            },

            # ===== Admission Requirements (~15%) =====
            {
                "question": "What is the ATAR requirement for Computer Science?",
                "ground_truth": "The ATAR requirement for the Bachelor of Computer Science at UNSW varies each year and depends on demand. Recent cut-offs have been around 93-96. Students also need to meet prerequisite subject requirements in Mathematics.",
                "category": "admission_requirements",
                "difficulty": "medium",
                "expected_context_keywords": ["ATAR", "Computer Science", "93", "Mathematics"]
            },
            {
                "question": "How do I apply to UNSW Computer Science?",
                "ground_truth": "Domestic students apply through UAC (Universities Admissions Centre) with their ATAR and HSC results. International students apply directly through UNSW or through an approved agent. Applications open around August for the following year's intake. Postgraduate applications go through UNSW directly.",
                "category": "admission_requirements",
                "difficulty": "medium",
                "expected_context_keywords": ["UAC", "apply", "ATAR", "HSC", "international"]
            },
            {
                "question": "What are the English requirements for international students?",
                "ground_truth": "International students applying to UNSW CSE programs need to meet English language requirements. For undergraduate programs, IELTS overall 6.5 (min 6.0 per band) or TOEFL iBT 90 (min 23 writing, 22 other) is typically required. Some programs may have higher requirements.",
                "category": "admission_requirements",
                "difficulty": "medium",
                "expected_context_keywords": ["IELTS", "6.5", "TOEFL", "international", "English"]
            },
            {
                "question": "Can I transfer from another university?",
                "ground_truth": "Yes, UNSW accepts transfer students. You can apply for credit transfer for courses completed at other recognised institutions. The application goes through UNSW Admissions and credit is assessed based on course equivalence. A minimum GPA is typically required.",
                "category": "admission_requirements",
                "difficulty": "medium",
                "expected_context_keywords": ["transfer", "credit", "university", "GPA"]
            },
            {
                "question": "What is the ATAR cutoff for Software Engineering?",
                "ground_truth": "The ATAR cutoff for the Bachelor of Software Engineering (Honours) at UNSW is typically around 96-98, higher than Computer Science due to the engineering honours component. The exact cutoff changes each year based on demand.",
                "category": "admission_requirements",
                "difficulty": "medium",
                "expected_context_keywords": ["ATAR", "Software Engineering", "96", "cutoff"]
            },
            {
                "question": "What are the entry requirements for Master of IT?",
                "ground_truth": "The Master of Information Technology at UNSW requires a completed bachelor's degree in any discipline with a minimum GPA equivalent. English language proficiency is required for non-native speakers (IELTS 6.5+). No prior IT background is needed.",
                "category": "admission_requirements",
                "difficulty": "medium",
                "expected_context_keywords": ["Master of IT", "bachelor's degree", "GPA", "IELTS"]
            },
            {
                "question": "When do applications open?",
                "ground_truth": "UNSW applications through UAC typically open in August for the following year. Direct international applications can be submitted year-round with key intake periods in Term 1 (February), Term 2 (June), and Term 3 (September). Postgraduate applications usually close a few weeks before term starts.",
                "category": "admission_requirements",
                "difficulty": "easy",
                "expected_context_keywords": ["applications", "August", "UAC", "Term 1", "Term 2"]
            },
            {
                "question": "Do I need work experience for postgraduate programs?",
                "ground_truth": "Most postgraduate Computer Science programs at UNSW do not require work experience. The Master of IT and Master of Computer Science are based on academic qualifications. However, some executive programs or MBA/IT combinations may require relevant experience.",
                "category": "admission_requirements",
                "difficulty": "easy",
                "expected_context_keywords": ["work experience", "postgraduate", "Master", "academic"]
            },

            # ===== Campus Facilities (~15%) =====
            {
                "question": "Where is the J17 building?",
                "ground_truth": "The J17 building, also known as the Ainsworth Building, houses part of the School of Computer Science and Engineering. It is located on the UNSW Kensington campus, near the main walkway. It contains offices, meeting rooms, and research labs.",
                "category": "campus_facilities",
                "difficulty": "easy",
                "expected_context_keywords": ["J17", "Ainsworth", "Kensington", "campus"]
            },
            {
                "question": "What facilities are in the CSE building?",
                "ground_truth": "The CSE building (K17) at UNSW contains computer labs with modern hardware, lecture theatres, tutorial rooms, a student common area (the CSE lounge), and research labs. Students have 24/7 access to the computer labs using their student ID card.",
                "category": "campus_facilities",
                "difficulty": "medium",
                "expected_context_keywords": ["CSE", "K17", "computer labs", "24/7", "student"]
            },
            {
                "question": "Where are the computer labs?",
                "ground_truth": "CSE computer labs are primarily located in the K17 (CSE Building) on levels 1 and 2. Additional labs may be available in other buildings on campus. Labs are equipped with Linux workstations and students can access them 24/7 with their student card.",
                "category": "campus_facilities",
                "difficulty": "easy",
                "expected_context_keywords": ["computer labs", "K17", "Linux", "24/7"]
            },
            {
                "question": "How do I get to UNSW from the city?",
                "ground_truth": "UNSW Kensington campus is accessible from Sydney CBD by bus (routes 891, 892, 893, 895 from Central Station) taking approximately 20-30 minutes. The light rail also connects to UNSW with a stop near campus. Driving is possible but parking is limited.",
                "category": "campus_facilities",
                "difficulty": "easy",
                "expected_context_keywords": ["bus", "Central Station", "light rail", "transport"]
            },
            {
                "question": "What computing resources are available for students?",
                "ground_truth": "CSE students have access to Linux lab machines (both on-campus and via SSH), personal storage on CSE servers, printing facilities, the CSE student email system, and various software licenses. Students can also access cloud computing resources through academic programs from AWS, Google, or Azure.",
                "category": "campus_facilities",
                "difficulty": "medium",
                "expected_context_keywords": ["Linux", "SSH", "servers", "computing", "resources"]
            },
            {
                "question": "Where is the library?",
                "ground_truth": "The main UNSW Library is located in the Library Building near the main walkway on Kensington campus. CSE students also frequently use the study spaces in the K17 building. The library offers online resources, study rooms, and a large collection of computing textbooks.",
                "category": "campus_facilities",
                "difficulty": "easy",
                "expected_context_keywords": ["library", "study", "Kensington", "books"]
            },
            {
                "question": "Where can I study on campus?",
                "ground_truth": "Students can study in the UNSW Library, CSE student lounge in K17, the Mathews building study spaces, various faculty common rooms, and outdoor areas. The library has bookable study rooms for group work. The K17 computer labs are available 24/7.",
                "category": "campus_facilities",
                "difficulty": "easy",
                "expected_context_keywords": ["study", "library", "K17", "lounge", "campus"]
            },
            {
                "question": "Where can I park at UNSW?",
                "ground_truth": "UNSW has paid parking available in several multi-storey car parks on the Kensington campus. Parking permits can be purchased online. Street parking around campus is limited and usually time-restricted. Public transport is recommended as parking can be expensive and spaces limited.",
                "category": "campus_facilities",
                "difficulty": "easy",
                "expected_context_keywords": ["parking", "car park", "campus", "permit"]
            },
        ]

        # Add metadata
        for item in ground_truth_data:
            item.update({
                "created_at": datetime.now().isoformat(),
                "source": "manual_creation",
                "version": "2.0"
            })

        self.ground_truth = ground_truth_data
        return ground_truth_data

    def generate_test_queries(self, sample_size: int = 50) -> List[Dict[str, Any]]:
        """Generate diverse test queries for evaluation"""

        if not self.ground_truth:
            self.create_unsw_ground_truth()

        # Create test queries from ground truth
        test_queries = []

        for gt in self.ground_truth:
            # Original question as a test query
            test_queries.append({
                "query": gt["question"],
                "ground_truth": gt["ground_truth"],
                "category": gt["category"],
                "difficulty": gt["difficulty"],
                "query_type": "direct",
                "expected_context_keywords": gt["expected_context_keywords"]
            })

            # Create rephrased variations
            variations = self._create_query_variations(gt)
            test_queries.extend(variations)

        # Add broad/general queries
        general_queries = [
            {
                "query": "Tell me about computer science at UNSW",
                "ground_truth": "UNSW offers undergraduate and postgraduate Computer Science programs through the School of Computer Science and Engineering. The Bachelor of Computer Science is a 3-year degree with various specialisations. The school is known for research and industry connections.",
                "category": "general_inquiries",
                "difficulty": "medium",
                "query_type": "broad",
                "expected_context_keywords": ["computer science", "UNSW", "programs", "degree"]
            },
            {
                "query": "What courses should I take in my first semester?",
                "ground_truth": "First-semester Computer Science students typically take COMP1511 (Programming Fundamentals), MATH1081 (Discrete Mathematics), MATH1131/MATH1141 (Mathematics 1A), and one elective. This provides the foundation for subsequent CS courses.",
                "category": "course_information",
                "difficulty": "medium",
                "query_type": "advisory",
                "expected_context_keywords": ["first semester", "COMP1511", "MATH1081", "MATH1131"]
            },
            {
                "query": "How do I apply to UNSW CSE?",
                "ground_truth": "Domestic students apply through UAC (Universities Admissions Centre). International students can apply directly through UNSW. You need to meet ATAR requirements and prerequisite subjects for undergraduate, or hold a bachelor's degree for postgraduate programs.",
                "category": "admission_requirements",
                "difficulty": "medium",
                "query_type": "procedural",
                "expected_context_keywords": ["apply", "UAC", "UNSW", "CSE", "ATAR"]
            },
        ]
        test_queries.extend(general_queries)

        # Limit to requested sample size
        if len(test_queries) > sample_size:
            random.seed(42)
            test_queries = random.sample(test_queries, sample_size)

        # Add metadata
        for i, query in enumerate(test_queries):
            query.update({
                "id": f"query_{i:03d}",
                "created_at": datetime.now().isoformat(),
                "version": "2.0"
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
