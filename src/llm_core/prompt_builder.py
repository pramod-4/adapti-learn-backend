
from typing import Dict, Any, List, Optional
from src.entities.profile import CognitiveProfile
from src.logger import logger


class PromptBuilder:
    """
    Builds adaptive prompts for the LLM based on user profile and knowledge context.
    
    Adapts prompts for:
    - Active vs Passive learners
    - Fast vs Slow learners  
    - Overview vs Detailed preferences
    - Short vs Long answer preferences
    """
    
    def __init__(self):
        self.base_templates = self._load_base_templates()
        self.style_modifiers = self._load_style_modifiers()
        self.subject_contexts = self._load_subject_contexts()
    
    def _load_base_templates(self) -> Dict[str, str]:
        """Load base prompt templates for different scenarios."""
        return {
            'explanation': """
You are an expert computer science tutor specializing in {subject}. 
A student has asked: "{query}"
{context_info}
{style_instructions}
{length_instructions}
{detail_instructions}
Please provide a clear, educational response that helps the student understand the concept.
Format your response in markdown with appropriate headers, bullet points, and code blocks where helpful.
""",
            
            'problem_solving': """
You are an expert computer science tutor helping with problem-solving in {subject}.
Student query: "{query}"
{context_info}
{style_instructions}
{length_instructions}
Please provide a step-by-step solution approach. Include:
- Problem analysis
- Solution strategy
- Implementation details (if applicable)
- Time/Space complexity (if relevant)
Format your response in markdown.
""",
            
            'comparison': """
You are an expert computer science tutor specializing in {subject}.
The student wants to understand: "{query}"
{context_info}
{style_instructions}
{length_instructions}
Please provide a comparative analysis that highlights:
- Key similarities and differences
- Use cases for each approach
- Trade-offs and considerations
Format your response in markdown with clear sections.
""",
            
            'implementation': """
You are an expert computer science tutor helping with implementation in {subject}.
Student request: "{query}"
{context_info}
{style_instructions}
{length_instructions}
Please provide:
- Code implementation with clear comments
- Explanation of key components
- Example usage
- Common pitfalls to avoid
Format your response in markdown with proper code blocks.
""",

            # DSA-specific template for integration with knowledge graph
            'dsa_explanation': """
You are an expert Data Structures and Algorithms tutor with deep knowledge of:
- Array and String manipulations
- Linked Lists, Stacks, Queues
- Trees, Graphs, and their traversals
- Sorting and Searching algorithms
- Time and Space complexity analysis
- Dynamic Programming and Greedy algorithms
- Hash tables and advanced data structures

Student query: "{query}"
{context_info}
{style_instructions}
{length_instructions}
{detail_instructions}

Your teaching approach should:
1. Start with intuitive explanations before diving into technical details
2. Use concrete examples and visual descriptions
3. Always discuss time/space complexity when relevant
4. Provide implementation insights and common pitfalls
5. Connect concepts to real-world applications
6. Adapt explanations to the student's cognitive learning style

Be encouraging and build confidence while maintaining technical accuracy.
Format your response in markdown with appropriate sections.
"""
        }
    
    def _load_style_modifiers(self) -> Dict[str, Dict[str, str]]:
        """Load style modifiers based on learner characteristics."""
        return {
            'active_learner': {
                'instruction': "The student is an active learner who asks many questions. Encourage further exploration and provide thought-provoking questions at the end.",
                'tone': "engaging and interactive"
            },
            'passive_learner': {
                'instruction': "The student is a passive learner. Provide comprehensive explanations and include motivating examples to maintain engagement.",
                'tone': "comprehensive and motivating"
            },
            'fast_learner': {
                'instruction': "The student learns quickly. You can use technical terminology and move through concepts at a good pace.",
                'tone': "concise and technical"
            },
            'slow_learner': {
                'instruction': "The student needs more time to process information. Break down complex concepts into smaller, digestible parts with clear transitions.",
                'tone': "patient and step-by-step"
            }
        }
    
    def _load_subject_contexts(self) -> Dict[str, str]:
        """Load subject-specific context instructions."""
        return {
            'OS': """
When explaining Operating Systems concepts, consider:
- Real-world system examples (Linux, Windows)
- Performance implications
- Security considerations
- Practical implementation details
""",
            'Networking': """
When explaining Networking concepts, consider:
- Protocol stack relationships
- Real-world network scenarios
- Performance and reliability aspects
- Security implications
""",
            'DSA': """
When explaining Data Structures & Algorithms concepts, consider:
- Time and space complexity analysis
- Practical use cases and applications
- Implementation trade-offs
- Visual representations when helpful
""",
            'DAA': """
When explaining Design & Analysis of Algorithms concepts, consider:
- Mathematical analysis and proofs
- Algorithm design paradigms
- Optimization techniques
- Comparative analysis of approaches
"""
        }
    
    def _determine_query_type(self, query: str) -> str:
        """Determine the type of query to select appropriate template."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['implement', 'code', 'write', 'program']):
            return 'implementation'
        elif any(word in query_lower for word in ['compare', 'difference', 'vs', 'versus', 'better']):
            return 'comparison'
        elif any(word in query_lower for word in ['solve', 'problem', 'algorithm for', 'how to']):
            return 'problem_solving'
        else:
            return 'explanation'
    
    def _build_context_info(self, kg_context: Dict) -> str:
        """Build context information from knowledge graph retrieval."""
        if not kg_context:
            return "Context: General computer science concept explanation."
        
        context_parts = []
        
        # Handle different context structures (from your KG vs general structure)
        if 'main_concepts' in kg_context:
            # Your DSA KG structure
            main_concepts = kg_context.get('main_concepts', [])
            if main_concepts:
                primary = main_concepts[0]
                concept_name = primary.get('name', 'Unknown concept')
                difficulty = primary.get('difficulty', 'medium')
                context_parts.append(f"Primary Concept: {concept_name} (Difficulty: {difficulty})")
                
                # Add node type information
                labels = primary.get('labels', [])
                if labels:
                    context_parts.append(f"Concept Type: {', '.join(labels)}")
            
            # Prerequisites from your KG
            prerequisites = kg_context.get('prerequisites', [])
            if prerequisites:
                prereq_names = [p.get('name', '') for p in prerequisites if p.get('name')]
                if prereq_names:
                    context_parts.append(f"Prerequisites: {', '.join(prereq_names)}")
            
            # Related concepts from your KG
            related = kg_context.get('related_concepts', [])
            if related:
                related_names = [r.get('name', '') for r in related if r.get('name')]
                if related_names:
                    context_parts.append(f"Related Concepts: {', '.join(related_names[:3])}")
    def _initialize_templates(self) -> Dict[str, PromptTemplate]:
        """Initialize prompt templates including DSA-specific ones"""
        templates = {
            # Your existing templates...
            "concept_explanation": PromptTemplate(
                name="concept_explanation",
                system_prompt="""You are an expert AI tutor specializing in Computer Science education, 
                specifically in Operating Systems, Computer Networking, Data Structures and Algorithms (DSA), 
                and Design and Analysis of Algorithms (DAA).

                Your goal is to provide educational explanations that are:
                1. Accurate and technically correct
                2. Adapted to the student's learning style and preferences
                3. Progressive and building on prerequisites
                4. Engaging and encouraging

                Always maintain a supportive and encouraging tone while being precise in your explanations.""",
                
                user_prompt_template="""Please explain the concept: "{concept_name}"

                **Student Context:**
                - Learning Style: {learning_style}
                - Preferred Response Length: {length_preference}
                - Detail Level: {detail_level}
                - Learning Pace: {pace_level}
                - Domain: {domain}
                - Current Knowledge Level: {difficulty_level}

                **Concept Information:**
                {concept_details}

                **Prerequisites (if any):**
                {prerequisites}

                **Student Query:**
                {user_query}

                Please provide an explanation that matches the student's learning preferences and builds appropriately on their background knowledge."""
            ),
            
            # NEW DSA-specific template
            "dsa_concept_explanation": PromptTemplate(
                name="dsa_concept_explanation",
                system_prompt="""You are an expert Data Structures and Algorithms tutor with deep knowledge of:
                - Array and String manipulations
                - Linked Lists, Stacks, Queues
                - Trees, Graphs, and their traversals
                - Sorting and Searching algorithms
                - Time and Space complexity analysis
                - Dynamic Programming and Greedy algorithms
                - Hash tables and advanced data structures

                Your teaching approach should:
                1. Start with intuitive explanations before diving into technical details
                2. Use concrete examples and visual descriptions
                3. Always discuss time/space complexity when relevant
                4. Provide implementation insights and common pitfalls
                5. Connect concepts to real-world applications
                6. Adapt explanations to the student's cognitive learning style

                Be encouraging and build confidence while maintaining technical accuracy.""",
                
                user_prompt_template="""**DSA Concept Explanation Request**

                **Concept:** {main_concept}
                **Student Query:** {user_query}

                **Student's Learning Profile:**
                - Learning Style: {learning_style}  
                - Pace Preference: {pace_level}
                - Detail Level: {detail_level}
                - Length Preference: {length_preference}

                **Knowledge Graph Context:**
                **Main Concepts Found:** {concept_names}
                **Prerequisites:** {prerequisites_text}
                **Related Concepts:** {related_concepts_text}
                **Difficulty Level:** {difficulty_info}

                **Personalized Learning Suggestions:**
                {learning_suggestions_text}

                **Instructions:**
                Please provide a comprehensive explanation that:
                1. Adapts to the student's learning style and preferences
                2. Builds on the identified prerequisites
                3. Uses the related concepts to provide context
                4. Includes time/space complexity analysis if applicable
                5. Provides practical examples and implementation tips
                6. Suggests next steps based on the student's profile

                {adaptive_instructions}"""
            )
        }
        return templates

# Enhanced build method for DSA context:
    async def build_adaptive_prompt(self, 
                                  user_query: str,
                                  cognitive_profile: CognitiveProfile,
                                  context: Dict[str, Any],
                                  template_name: str = "concept_explanation") -> List[Dict[str, str]]:
        """Build adaptive prompt with enhanced DSA context handling"""
        
        try:
            template = self.templates.get(template_name)
            if not template:
                template = self.templates["concept_explanation"]
            
            # Enhanced context formatting for DSA
            if template_name == "dsa_concept_explanation":
                return await self._build_dsa_specific_prompt(
                    user_query, cognitive_profile, context, template
                )
            else:
                # Use existing method for other templates
                return await self._build_general_prompt(
                    user_query, cognitive_profile, context, template
                )
                
        except Exception as e:
            logger.error(f"Failed to build adaptive prompt: {e}")
            # Fallback to simple prompt
            return [
                {"role": "system", "content": "You are a helpful AI tutor for DSA and computer science topics."},
                {"role": "user", "content": user_query}
            ]
    
    async def _build_dsa_specific_prompt(self, user_query, cognitive_profile, context, template):
        """Build DSA-specific adaptive prompt"""
        
        # Interpret cognitive profile for DSA learning
        learning_style = self._interpret_dsa_learning_style(cognitive_profile)
        length_preference = self._get_length_preference(cognitive_profile)
        detail_level = self._get_dsa_detail_level(cognitive_profile)
        pace_level = self._get_pace_level(cognitive_profile)
        
        # Format DSA-specific context
        main_concepts = context.get('main_concepts', [])
        concept_names = [c.get('name', '') for c in main_concepts[:3]]
        
        prerequisites = context.get('prerequisites', [])
        prerequisites_text = self._format_dsa_prerequisites(prerequisites)
        
        related_concepts = context.get('related_concepts', [])
        related_concepts_text = self._format_dsa_related(related_concepts)
        
        difficulty_info = context.get('difficulty_info', {})
        difficulty_text = self._format_dsa_difficulty(difficulty_info)
        
        learning_suggestions = context.get('learning_suggestions', [])
        learning_suggestions_text = '\n'.join([f"• {suggestion}" for suggestion in learning_suggestions])
        
        # Build DSA-specific prompt
        user_prompt = template.user_prompt_template.format(
            main_concept=concept_names[0] if concept_names else "the requested concept",
            user_query=user_query,
            learning_style=learning_style,
            pace_level=pace_level,
            detail_level=detail_level,
            length_preference=length_preference,
            concept_names=', '.join(concept_names) if concept_names else "Not found in knowledge graph",
            prerequisites_text=prerequisites_text,
            related_concepts_text=related_concepts_text,
            difficulty_info=difficulty_text,
            learning_suggestions_text=learning_suggestions_text,
            adaptive_instructions=self._get_dsa_adaptive_instructions(cognitive_profile)
        )
        
        return [
            {"role": "system", "content": template.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def _interpret_dsa_learning_style(self, profile):
        """DSA-specific learning style interpretation"""
        if profile.active_vs_passive > 0.6 and profile.overview_vs_detailed > 0.6:
            return "Implementation-focused (learns by coding and analyzing algorithms step-by-step)"
        elif profile.active_vs_passive > 0.6 and profile.overview_vs_detailed <= 0.4:
            return "Example-driven (learns through concrete examples and quick problem-solving)"
        elif profile.active_vs_passive <= 0.4 and profile.overview_vs_detailed > 0.6:
            return "Theory-first (prefers detailed algorithmic analysis before implementation)"
        else:
            return "Structured (prefers clear explanations with organized step-by-step approach)"
    
    def _get_dsa_detail_level(self, profile):
        """DSA-specific detail level"""
        if profile.overview_vs_detailed > 0.7:
            return "Comprehensive with complexity analysis, implementation details, and edge cases"
        elif profile.overview_vs_detailed < 0.3:
            return "High-level overview focusing on key algorithmic concepts"
        else:
            return "Balanced explanation with key points, examples, and basic complexity analysis"
    
    def _format_dsa_prerequisites(self, prerequisites):
        """Format DSA prerequisites for prompt"""
        if not prerequisites:
            return "No specific prerequisites identified."
        
        formatted = []
        for prereq in prerequisites[:3]:
            name = prereq.get('name', '')
            difficulty = prereq.get('difficulty', '')
            formatted.append(f"• {name} ({difficulty} level)")
        
        return '\n'.join(formatted)
    
    def _format_dsa_related(self, related_concepts):
        """Format DSA related concepts for prompt"""
        if not related_concepts:
            return "No related concepts identified."
        
        formatted = []
        for concept in related_concepts[:3]:
            name = concept.get('name', '')
            formatted.append(f"• {name}")
        
        return '\n'.join(formatted)
    
    def _format_dsa_difficulty(self, difficulty_info):
        """Format DSA difficulty information"""
        if not difficulty_info:
            return "Difficulty level not specified"
        
        main_difficulty = difficulty_info.get('main_concept_difficulty', 'unknown')
        user_pace = difficulty_info.get('user_pace_preference', 'moderate')
        approach = difficulty_info.get('recommended_approach', 'balanced')
        
        return f"Concept difficulty: {main_difficulty} | User pace: {user_pace} | Approach: {approach}"
    
    def _get_dsa_adaptive_instructions(self, profile):
        """DSA-specific adaptive instructions"""
        instructions = []
        
        if profile.active_vs_passive > 0.6:
            instructions.append("Include pseudocode or implementation snippets where appropriate.")
            instructions.append("Suggest hands-on coding exercises or problems to solve.")
        
        if profile.overview_vs_detailed > 0.6:
            instructions.append("Provide detailed time and space complexity analysis.")
            instructions.append("Discuss edge cases and optimization opportunities.")
        
        if profile.fast_vs_slow > 0.7:
            instructions.append("Feel free to mention advanced variations or optimizations.")
            instructions.append("Connect to more complex algorithms or data structures.")
        
        if profile.confidence < 0.3:
            instructions.append("Use encouraging language and emphasize that DSA concepts build on each other.")
            instructions.append("Start with simpler examples before moving to complex cases.")
        
        return ' '.join(instructions) if instructions else ""
