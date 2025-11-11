BASE_PROMPT = """
You are an expert Computer Science educator generating structured and concise study notes for the subject "Operating Systems" for undergraduate students.

Generate technically accurate, well-organized, and easy-to-read notes for ALL FIVE UNITS below.

The output MUST be a single valid JSON object (no markdown, no formatting symbols, no escape characters, no newlines like \\n). 
It should be directly parsable by a JSON parser without modification.

Each unit must strictly follow this JSON structure:

{
  "unit": "Unit title",
  "topics": [
    {
      "title": "Topic name",
      "overview": "Brief introduction to the topic.",
      "theory": "Concise and clear explanation (maximum 6-8 sentences).",
      "example_or_analogy": "1-2 line example or real-world analogy to make the concept intuitive.",
      "key_points": ["Important points or steps (each short and clear)"],
      "applications": ["Real-life or practical relevance of the concept"]
    }
  ]
}

Rules for generation:
1. Output ONLY one valid JSON object (no markdown, no text outside JSON).
2. Use plain text only — no **, _, headers, or escape characters.
3. Each topic should be concise but technically accurate.
4. Each explanation (theory) should have a maximum of 6-8 sentences.
5. Maintain the exact key names and order for every topic.
6. Include all five units exactly in sequence.
7. Do not include code, diagrams, or quizzes.

Now generate notes for these units:

Unit 1: Introduction to Operating Systems
1. What is an Operating System?
2. Objectives and Functions of an OS
3. Types of Operating Systems
4. System Components and Structure
5. OS Architecture (Monolithic, Layered, Microkernel)

Unit 2: Process Management
1. Process Concept and Process States
2. Process Control Block (PCB)
3. CPU Scheduling Algorithms (FCFS, SJF, RR, Priority)
4. Interprocess Communication (IPC)
5. Threads and Multithreading

Unit 3: Memory Management
1. Address Binding and Memory Allocation
2. Contiguous Memory Allocation
3. Paging and Segmentation
4. Virtual Memory and Demand Paging
5. Page Replacement Algorithms

Unit 4: File Systems and Storage Management
1. File Concepts and Access Methods
2. Directory Structures
3. Disk Scheduling Algorithms (FCFS, SSTF, SCAN, C-SCAN)
4. File System Implementation
5. Disk Management and RAID

Unit 5: Deadlocks and Synchronization
1. Deadlock Conditions and Resource Allocation Graph
2. Deadlock Prevention, Avoidance, and Detection
3. Banker’s Algorithm
4. Process Synchronization and Semaphores
5. Classical Synchronization Problems (Producer-Consumer, Readers-Writers, Dining Philosophers)
"""


STYLE_PROMPTS = {
    "sensing": """
The learner has a sensing learning style.
Modify your explanations to include practical and real-world context.
Focus on concrete examples, hands-on scenarios, and step-by-step summaries.
Avoid excessive abstraction and theoretical generalization.
Add these fields to each topic:
"real_world_examples": ["Concrete examples illustrating the topic"],
"step_by_step_summary": ["Simple ordered steps for practical understanding"]
""",

    "intuitive": """
The learner has an intuitive learning style.
Focus on abstract reasoning, conceptual connections, and theoretical insights.
Highlight underlying principles and relationships between ideas rather than concrete examples.
Add these fields to each topic:
"conceptual_focus": ["Abstract ideas or theories to think about"],
"connections": ["Links to related topics or broader computer science principles"]
""",

    "active": """
The learner has an active learning style.
Include thought-provoking mini-tasks, quick scenarios, or practical engagement questions.
Encourage doing, experimenting, and applying.
Add these fields to each topic:
"engagement_task": "Short activity or question for the learner to try",
"scenario": "Real-world situation where the concept can be applied interactively"
""",

    "reflective": """
The learner has a reflective learning style.
Encourage introspection and self-assessment.
Add a brief summary or question that promotes personal reflection after each topic.
Add these fields to each topic:
"self_reflection": "A short reflective question or thought prompt",
"summary_note": "One-line reflective takeaway about the topic"
"""
}
