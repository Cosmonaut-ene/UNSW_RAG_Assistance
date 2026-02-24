"""
Expanded evaluation datasets for comprehensive 30+ query testing
"""

def create_comprehensive_ground_truth():
    """Create comprehensive ground truth with 30+ UNSW-specific questions"""
    
    comprehensive_data = [
        # Course Information (8 questions)
        {
            "question": "What is COMP9900?",
            "ground_truth_answer": "COMP9900 is a capstone project course for computer science students at UNSW. Students work in teams to develop a substantial software project over a semester, applying knowledge from previous coursework to real-world problems.",
            "category": "course_information",
            "difficulty": "easy",
            "expected_context_keywords": ["capstone", "project", "COMP9900", "software", "team"]
        },
        {
            "question": "What is COMP2521?",
            "ground_truth_answer": "COMP2521 (Data Structures and Algorithms) teaches fundamental data structures like linked lists, trees, graphs, and hash tables, along with algorithms for searching, sorting, and graph traversal. It's a core second-year subject.",
            "category": "course_information", 
            "difficulty": "medium",
            "expected_context_keywords": ["COMP2521", "data structures", "algorithms", "trees", "graphs"]
        },
        {
            "question": "What is COMP1511?",
            "ground_truth_answer": "COMP1511 (Programming Fundamentals) is an introductory programming course that teaches fundamental programming concepts using the C programming language. It covers variables, functions, arrays, and basic algorithms.",
            "category": "course_information",
            "difficulty": "easy", 
            "expected_context_keywords": ["COMP1511", "programming", "fundamentals", "C language"]
        },
        {
            "question": "What is COMP3311?",
            "ground_truth_answer": "COMP3311 (Database Systems) covers relational database design, SQL, database theory, and database management systems. Students learn about normalization, transactions, and database implementation.",
            "category": "course_information",
            "difficulty": "medium",
            "expected_context_keywords": ["COMP3311", "database", "SQL", "relational"]
        },
        {
            "question": "What is COMP2511?",
            "ground_truth_answer": "COMP2511 (Object-Oriented Design & Programming) teaches object-oriented programming concepts including classes, inheritance, polymorphism, and design patterns using Java. It emphasizes software design principles.",
            "category": "course_information",
            "difficulty": "medium",
            "expected_context_keywords": ["COMP2511", "object-oriented", "Java", "design patterns"]
        },
        {
            "question": "What programming languages are taught in first year?",
            "ground_truth_answer": "First-year computer science students at UNSW typically learn C in COMP1511 (Programming Fundamentals) and may be introduced to Python in other courses. Some courses also cover basic web technologies like HTML and CSS.",
            "category": "course_information",
            "difficulty": "medium",
            "expected_context_keywords": ["first year", "C", "Python", "COMP1511"]
        },
        {
            "question": "What is the capstone project course?",
            "ground_truth_answer": "The capstone project course is COMP9900, where students work in teams to develop a substantial software application. It integrates knowledge from previous courses and simulates real-world software development.",
            "category": "course_information",
            "difficulty": "easy",
            "expected_context_keywords": ["capstone", "COMP9900", "software", "teams"]
        },
        {
            "question": "What is software engineering methodology?",
            "ground_truth_answer": "Software engineering methodology courses at UNSW teach systematic approaches to software development including agile methodologies, project management, requirements analysis, testing strategies, and software lifecycle management.",
            "category": "course_information",
            "difficulty": "hard",
            "expected_context_keywords": ["software engineering", "methodology", "agile", "testing"]
        },
        
        # Prerequisites (6 questions)
        {
            "question": "What are the prerequisites for COMP9900?",
            "ground_truth_answer": "Prerequisites for COMP9900 include COMP2511 (Object-Oriented Design & Programming) and COMP3311 (Database Systems), plus completion of at least 102 units including core computer science subjects.",
            "category": "prerequisites",
            "difficulty": "medium",
            "expected_context_keywords": ["prerequisites", "COMP2511", "COMP3311", "102 units"]
        },
        {
            "question": "What are the prerequisites for COMP2521?",
            "ground_truth_answer": "The main prerequisite for COMP2521 is COMP1511 (Programming Fundamentals). Students should have a solid understanding of basic programming concepts and C programming.",
            "category": "prerequisites", 
            "difficulty": "easy",
            "expected_context_keywords": ["prerequisites", "COMP2521", "COMP1511"]
        },
        {
            "question": "Do I need COMP1511 before COMP2511?",
            "ground_truth_answer": "Yes, COMP1511 is typically a prerequisite for COMP2511. Students need foundational programming skills before advancing to object-oriented programming concepts.",
            "category": "prerequisites",
            "difficulty": "easy",
            "expected_context_keywords": ["COMP1511", "COMP2511", "prerequisite"]
        },
        {
            "question": "What math subjects are required for computer science?",
            "ground_truth_answer": "Computer science students typically need mathematics subjects including MATH1081 (Discrete Mathematics), MATH1131 (Mathematics 1A), and MATH1241 (Higher Mathematics 1A). These provide essential mathematical foundations.",
            "category": "prerequisites",
            "difficulty": "medium", 
            "expected_context_keywords": ["mathematics", "MATH1081", "MATH1131", "discrete"]
        },
        {
            "question": "Can I take COMP3311 without COMP2521?",
            "ground_truth_answer": "COMP3311 typically requires COMP2521 as a prerequisite, as database systems concepts build on data structures and algorithms knowledge. Check current prerequisites before enrolling.",
            "category": "prerequisites",
            "difficulty": "medium",
            "expected_context_keywords": ["COMP3311", "COMP2521", "prerequisite"]
        },
        {
            "question": "What are the entry requirements for postgraduate CS courses?",
            "ground_truth_answer": "Postgraduate computer science courses typically require a bachelor's degree with relevant background. Some courses may require specific undergraduate subjects or work experience. International students need English proficiency requirements.",
            "category": "prerequisites",
            "difficulty": "hard",
            "expected_context_keywords": ["postgraduate", "bachelor", "requirements", "English proficiency"]
        },
        
        # Degree Programs (8 questions)
        {
            "question": "What is the Bachelor of Computer Science degree?",
            "ground_truth_answer": "The Bachelor of Computer Science is a 3-year undergraduate program at UNSW covering programming, algorithms, software engineering, and computer systems. Students complete 144 units including core subjects and electives.",
            "category": "degree_programs",
            "difficulty": "easy",
            "expected_context_keywords": ["Bachelor", "Computer Science", "3-year", "144 units"]
        },
        {
            "question": "What is the Master of Information Technology program?",
            "ground_truth_answer": "The Master of Information Technology (MIT) is a 2-year postgraduate program designed for students from non-computing backgrounds. It covers programming, databases, web development, and prepares students for IT careers.",
            "category": "degree_programs",
            "difficulty": "medium", 
            "expected_context_keywords": ["Master", "Information Technology", "2-year", "postgraduate"]
        },
        {
            "question": "How long is the Computer Science degree?",
            "ground_truth_answer": "The Bachelor of Computer Science at UNSW is a 3-year full-time degree requiring 144 units of credit. Part-time study options are available, extending the duration accordingly.",
            "category": "degree_programs",
            "difficulty": "easy",
            "expected_context_keywords": ["3-year", "144 units", "full-time", "part-time"]
        },
        {
            "question": "Can I do a double degree with Computer Science?",
            "ground_truth_answer": "Yes, UNSW offers double degree combinations with Computer Science including Commerce, Mathematics, Science, and Engineering. Double degrees typically take 5 years and provide broader career opportunities.",
            "category": "degree_programs",
            "difficulty": "medium",
            "expected_context_keywords": ["double degree", "Commerce", "Mathematics", "5 years"]
        },
        {
            "question": "What specializations are available in Computer Science?",
            "ground_truth_answer": "Computer Science students can specialize in areas like Artificial Intelligence, Cybersecurity, Software Engineering, Database Systems, Computer Graphics, and Human-Computer Interaction through elective choices.",
            "category": "degree_programs",
            "difficulty": "medium",
            "expected_context_keywords": ["specializations", "AI", "cybersecurity", "software engineering"]
        },
        {
            "question": "What is the Master of Engineering in Software Engineering?",
            "ground_truth_answer": "The Master of Engineering in Software Engineering is an advanced degree focusing on large-scale software development, system architecture, project management, and industry practices. It typically requires 2 years of study.",
            "category": "degree_programs", 
            "difficulty": "hard",
            "expected_context_keywords": ["Master", "Software Engineering", "architecture", "2 years"]
        },
        {
            "question": "What is the difference between CS and Software Engineering degrees?",
            "ground_truth_answer": "Computer Science focuses on theoretical foundations and broad computing concepts, while Software Engineering emphasizes practical software development, project management, and industry practices. Both lead to similar career paths.",
            "category": "degree_programs",
            "difficulty": "hard",
            "expected_context_keywords": ["Computer Science", "Software Engineering", "theoretical", "practical"]
        },
        {
            "question": "Are there part-time study options?",
            "ground_truth_answer": "Yes, UNSW offers part-time study options for most computer science programs. Part-time students typically take fewer subjects per semester, extending the degree duration but providing flexibility for working students.",
            "category": "degree_programs",
            "difficulty": "easy",
            "expected_context_keywords": ["part-time", "flexibility", "fewer subjects", "working students"]
        },
        
        # Campus and Facilities (4 questions)
        {
            "question": "Where is the J17 building located?",
            "ground_truth_answer": "The J17 building (Computer Science and Engineering Building) is located on UNSW Kensington campus. It houses the School of Computer Science and Engineering with lecture theatres, computer labs, and faculty offices.",
            "category": "campus_facilities",
            "difficulty": "easy",
            "expected_context_keywords": ["J17", "CSE building", "Kensington campus", "computer labs"]
        },
        {
            "question": "What facilities are available in the CSE building?",
            "ground_truth_answer": "The CSE building contains computer labs with latest hardware/software, lecture theatres, tutorial rooms, student common areas, specialized robotics facilities, and quiet study spaces for students.",
            "category": "campus_facilities",
            "difficulty": "medium",
            "expected_context_keywords": ["computer labs", "lecture theatres", "robotics", "study spaces"]
        },
        {
            "question": "How do I get to UNSW from the city?",
            "ground_truth_answer": "You can reach UNSW Kensington campus from Sydney CBD via buses (routes 891, 894, 895, L94), or by train to Central/Eddy Ave then bus. The campus is also accessible by car with paid parking available.",
            "category": "campus_facilities",
            "difficulty": "easy",
            "expected_context_keywords": ["buses", "trains", "Central station", "parking"]
        },
        {
            "question": "What computing resources are available to students?",
            "ground_truth_answer": "Students have access to modern computer labs, high-performance computing clusters, software development tools, cloud computing resources, and 24/7 remote access to university systems.",
            "category": "campus_facilities",
            "difficulty": "medium",
            "expected_context_keywords": ["computer labs", "cloud computing", "remote access", "software tools"]
        },
        
        # Admission Requirements (4 questions)
        {
            "question": "What is the ATAR requirement for Computer Science?",
            "ground_truth_answer": "The ATAR requirement for Bachelor of Computer Science at UNSW is typically around 95+ (varies annually). Students also need Mathematics Extension 1 or Extension 2 as prerequisites.",
            "category": "admission_requirements", 
            "difficulty": "medium",
            "expected_context_keywords": ["ATAR", "95", "Mathematics Extension", "prerequisites"]
        },
        {
            "question": "How do I apply to UNSW Computer Science?",
            "ground_truth_answer": "Apply through UAC (Universities Admissions Centre) for undergraduate programs. International students apply directly to UNSW. Applications typically open in August for the following year with multiple intake periods.",
            "category": "admission_requirements",
            "difficulty": "easy",
            "expected_context_keywords": ["UAC", "application", "international students", "August"]
        },
        {
            "question": "What are the English requirements for international students?",
            "ground_truth_answer": "International students need IELTS 6.5 overall (6.0 in each band) or TOEFL equivalent. Some programs may have higher requirements. Alternative English tests and bridging programs are also accepted.",
            "category": "admission_requirements",
            "difficulty": "medium", 
            "expected_context_keywords": ["IELTS", "TOEFL", "6.5", "international students"]
        },
        {
            "question": "Can I transfer from another university?",
            "ground_truth_answer": "Yes, credit transfers from other universities are possible. Applications are assessed individually based on equivalent subjects completed. Some subjects may need to be repeated depending on curriculum differences.",
            "category": "admission_requirements",
            "difficulty": "medium",
            "expected_context_keywords": ["credit transfer", "equivalent subjects", "assessment", "curriculum"]
        }
    ]
    
    # Add metadata to all items
    from datetime import datetime
    for item in comprehensive_data:
        item.update({
            "created_at": datetime.now().isoformat(),
            "source": "expanded_manual_creation",
            "version": "2.0"
        })
    
    return comprehensive_data

def generate_comprehensive_test_queries(ground_truth_data, target_count=30):
    """Generate comprehensive test queries from ground truth data"""
    
    test_queries = []
    
    for i, gt in enumerate(ground_truth_data):
        # Original question
        test_queries.append({
            "id": f"query_{i:03d}_original",
            "query": gt["question"],
            "expected_answer": gt["ground_truth_answer"], 
            "category": gt["category"],
            "difficulty": gt["difficulty"],
            "query_type": "direct",
            "expected_context_keywords": gt["expected_context_keywords"]
        })
        
        # Create variations for more queries
        variations = create_query_variations(gt, i)
        test_queries.extend(variations)
        
        # Stop if we've reached target count
        if len(test_queries) >= target_count:
            break
    
    # Add some general queries if we need more
    if len(test_queries) < target_count:
        general_queries = create_general_queries()
        test_queries.extend(general_queries[:target_count - len(test_queries)])
    
    # Add metadata
    from datetime import datetime
    for query in test_queries:
        query.update({
            "created_at": datetime.now().isoformat(),
            "version": "2.0"
        })
    
    return test_queries[:target_count]

def create_query_variations(ground_truth_item, index):
    """Create variations of a ground truth question"""
    variations = []
    base_question = ground_truth_item["question"]
    
    # Variation patterns based on question type
    if "What is" in base_question:
        subject = extract_subject(base_question)
        if subject:
            variations.extend([
                {
                    "id": f"query_{index:03d}_tell_me",
                    "query": f"Tell me about {subject}",
                    "expected_answer": ground_truth_item["ground_truth_answer"],
                    "category": ground_truth_item["category"],
                    "difficulty": ground_truth_item["difficulty"],
                    "query_type": "rephrased",
                    "expected_context_keywords": ground_truth_item["expected_context_keywords"]
                },
                {
                    "id": f"query_{index:03d}_explain",
                    "query": f"Can you explain {subject}?",
                    "expected_answer": ground_truth_item["ground_truth_answer"],
                    "category": ground_truth_item["category"], 
                    "difficulty": ground_truth_item["difficulty"],
                    "query_type": "rephrased",
                    "expected_context_keywords": ground_truth_item["expected_context_keywords"]
                }
            ])
    
    if "prerequisites" in base_question.lower():
        subject = extract_course_code(base_question)
        if subject:
            variations.append({
                "id": f"query_{index:03d}_prereq_variation", 
                "query": f"What do I need before taking {subject}?",
                "expected_answer": ground_truth_item["ground_truth_answer"],
                "category": ground_truth_item["category"],
                "difficulty": ground_truth_item["difficulty"],
                "query_type": "rephrased",
                "expected_context_keywords": ground_truth_item["expected_context_keywords"]
            })
    
    return variations

def create_general_queries():
    """Create general queries to fill test set"""
    return [
        {
            "id": "general_001",
            "query": "Tell me about computer science at UNSW",
            "category": "general_inquiries",
            "difficulty": "medium", 
            "query_type": "broad",
            "expected_context_keywords": ["computer science", "UNSW", "programs"]
        },
        {
            "id": "general_002", 
            "query": "What should I study in my first semester?",
            "category": "course_information",
            "difficulty": "medium",
            "query_type": "advisory",
            "expected_context_keywords": ["first semester", "courses", "COMP1511"]
        },
        {
            "id": "general_003",
            "query": "How do I become a software engineer?",
            "category": "degree_programs", 
            "difficulty": "medium",
            "query_type": "career",
            "expected_context_keywords": ["software engineer", "degree", "career path"]
        }
    ]

def extract_subject(question):
    """Extract main subject from 'What is X?' questions"""
    import re
    match = re.search(r'What is (.+?)\?', question)
    return match.group(1) if match else None

def extract_course_code(question):
    """Extract course code from question"""
    import re
    match = re.search(r'(COMP\d{4})', question)
    return match.group(1) if match else None