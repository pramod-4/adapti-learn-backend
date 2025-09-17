
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio

from src.entities.profile import CognitiveProfile
from src.entities.knowledge import ConceptNode, Domain
from src.database.postgres import postgres_repo
from src.database.neo4j import neo4j_repo
from src.feedback.tracker import feedback_tracker
from src.logger import logger


class RecommendationEngine:
    """Generates personalized learning recommendations"""
    
    async def get_personalized_recommendations(self, user_id: str) -> Dict[str, Any]:
        """Generate comprehensive personalized recommendations"""
        try:
            # Get user's cognitive profile and progress
            cognitive_profile = await postgres_repo.get_cognitive_profile(user_id)
            progress_summary = await feedback_tracker.get_user_progress_summary(user_id)
            
            if not cognitive_profile:
                return {"message": "Insufficient data for personalized recommendations"}
            
            recommendations = {
                "next_concepts": await self._recommend_next_concepts(user_id, progress_summary),
                "study_approach": await self._recommend_study_approach(cognitive_profile),
                "difficulty_adjustment": await self._recommend_difficulty_adjustment(user_id, progress_summary),
                "learning_path": await self._recommend_learning_path(user_id, progress_summary),
                "study_schedule": await self._recommend_study_schedule(cognitive_profile, progress_summary)
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations for user {user_id}: {e}")
            return {"error": "Could not generate recommendations"}
    
    async def _recommend_next_concepts(self, user_id: str, 
                                     progress_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recommend next concepts to study"""
        recommendations = []
        
        # Find concepts with low mastery that need reinforcement
        if 'domains' in progress_summary:
            for domain, domain_data in progress_summary['domains'].items():
                if domain_data['avg_mastery'] < 0.7:  # Needs improvement
                    # Get related concepts from knowledge graph
                    try:
                        from src.entities.knowledge import SearchQuery, Domain as KnowledgeDomain
                        domain_enum = KnowledgeDomain(domain)
                        
                        # Search for beginner concepts in this domain
                        search_query = SearchQuery(
                            query_text="basic fundamentals",
                            domain_filter=domain_enum,
                            difficulty_filter=None,
                            limit=3
                        )
                        
                        concepts = await neo4j_repo.search_concepts(search_query)
                        for result in concepts[:2]:  # Top 2 recommendations
                            recommendations.append({
                                "concept": result.concept.concept_name,
                                "domain": result.concept.domain,
                                "difficulty": result.concept.difficulty_level,
                                "reason": f"Strengthen foundation in {domain}",
                                "estimated_time": "20-30 minutes"
                            })
                    except Exception as e:
                        logger.warning(f"Could not get concept recommendations for {domain}: {e}")
        
        # If no specific recommendations, suggest popular beginner concepts
        if not recommendations:
            recommendations = [
                {
                    "concept": "Process Management",
                    "domain": "Operating Systems", 
                    "difficulty": 2,
                    "reason": "Fundamental OS concept",
                    "estimated_time": "25 minutes"
                },
                {
                    "concept": "Basic Data Structures",
                    "domain": "Data Structures and Algorithms",
                    "difficulty": 1, 
                    "reason": "Essential programming foundation",
                    "estimated_time": "30 minutes"
                }
            ]
        
        return recommendations
    
    async def _recommend_study_approach(self, profile: CognitiveProfile) -> Dict[str, Any]:
        """Recommend study approach based on cognitive profile"""
        approach = {
            "primary_style": "",
            "techniques": [],
            "session_structure": {},
            "content_preferences": {}
        }
        
        # Determine primary learning style
        if profile.active_vs_passive > 0.6 and profile.overview_vs_detailed > 0.6:
            approach["primary_style"] = "Active Deep Learning"
            approach["techniques"] = [
                "Work through detailed examples step-by-step",
                "Ask follow-up questions to explore edge cases", 
                "Implement concepts in code to reinforce understanding",
                "Create mind maps connecting related concepts"
            ]
        elif profile.active_vs_passive > 0.6 and profile.overview_vs_detailed <= 0.4:
            approach["primary_style"] = "Active Exploratory Learning"
            approach["techniques"] = [
                "Start with high-level concept overviews",
                "Use interactive examples and demonstrations",
                "Focus on practical applications and use cases",
                "Engage in Q&A to clarify understanding"
            ]
        elif profile.active_vs_passive <= 0.4 and profile.overview_vs_detailed > 0.6:
            approach["primary_style"] = "Reflective Deep Learning"
            approach["techniques"] = [
                "Read comprehensive explanations carefully",
                "Take detailed notes and create study guides",
                "Review concepts multiple times for mastery",
                "Study prerequisite concepts thoroughly"
            ]
        else:
            approach["primary_style"] = "Reflective Overview Learning"
            approach["techniques"] = [
                "Focus on clear, concise concept summaries",
                "Use structured learning materials",
                "Review key points regularly",
                "Build understanding incrementally"
            ]
        
        # Session structure recommendations
        if profile.fast_vs_slow > 0.6:
            approach["session_structure"] = {
                "session_length": "45-60 minutes",
                "concepts_per_session": "2-3",
                "break_frequency": "Every 20 minutes"
            }
        else:
            approach["session_structure"] = {
                "session_length": "30-45 minutes", 
                "concepts_per_session": "1-2",
                "break_frequency": "Every 15 minutes"
            }
        
        # Content preferences
        approach["content_preferences"] = {
            "explanation_length": "Long detailed" if profile.long_vs_short > 0.6 else "Concise focused",
            "example_complexity": "Advanced" if profile.fast_vs_slow > 0.6 else "Basic to intermediate",
            "interaction_level": "High" if profile.active_vs_passive > 0.6 else "Moderate"
        }
        
        return approach
    
    async def _recommend_difficulty_adjustment(self, user_id: str, 
                                             progress_summary: Dict[str, Any]) -> Dict[str, str]:
        """Recommend difficulty adjustments based on performance"""
        
        if not progress_summary or 'overall_metrics' not in progress_summary:
            return {"adjustment": "maintain", "reason": "Insufficient data for adjustment"}
        
        avg_mastery = progress_summary['overall_metrics'].get('avg_mastery', 0.5)
        feedback_data = progress_summary.get('feedback', {})
        
        # Analyze performance indicators
        if avg_mastery > 0.8 and feedback_data.get('avg_rating', 3) >= 4:
            return {
                "adjustment": "increase", 
                "reason": "Strong mastery across concepts, ready for more challenging material"
            }
        elif avg_mastery < 0.4 or feedback_data.get('negative_feedback', 0) > 3:
            return {
                "adjustment": "decrease",
                "reason": "Struggling with current difficulty, recommend focusing on fundamentals"
            }
        else:
            return {
                "adjustment": "maintain",
                "reason": "Current difficulty level appears appropriate"
            }
    
    async def _recommend_learning_path(self, user_id: str, 
                                     progress_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend structured learning path"""
        
        path_recommendation = {
            "suggested_domain": "",
            "path_structure": [],
            "estimated_completion": "",
            "rationale": ""
        }
        
        # Determine domain focus based on progress and gaps
        if 'domains' in progress_summary:
            domain_scores = {}
            for domain, data in progress_summary['domains'].items():
                # Score based on engagement and mastery gaps
                engagement_score = data['concepts_studied'] * data['total_time']
                mastery_gap = 1.0 - data['avg_mastery']
                domain_scores[domain] = engagement_score * mastery_gap
            
            if domain_scores:
                recommended_domain = max(domain_scores.items(), key=lambda x: x[1])[0]
                path_recommendation["suggested_domain"] = recommended_domain
                
                # Create learning path structure
                path_recommendation["path_structure"] = [
                    {"stage": "Foundation", "concepts": ["Basic concepts", "Core principles"], "weeks": 2},
                    {"stage": "Intermediate", "concepts": ["Applied concepts", "Problem solving"], "weeks": 3}, 
                    {"stage": "Advanced", "concepts": ["Complex applications", "Optimization"], "weeks": 2}
                ]
                
                path_recommendation["estimated_completion"] = "6-8 weeks"
                path_recommendation["rationale"] = f"High engagement but room for improvement in {recommended_domain}"
        
        return path_recommendation
    
    async def _recommend_study_schedule(self, profile: CognitiveProfile, 
                                      progress_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend optimal study schedule"""
        
        schedule = {
            "sessions_per_week": 0,
            "session_duration": "",
            "best_times": [],
            "weekly_goals": {}
        }
        
        # Base recommendations on learning speed and engagement
        if profile.fast_vs_slow > 0.6:
            schedule["sessions_per_week"] = 4
            schedule["session_duration"] = "45-60 minutes"
            schedule["weekly_goals"] = {"concepts": 6, "practice_problems": 10}
        elif profile.fast_vs_slow < 0.4:
            schedule["sessions_per_week"] = 3
            schedule["session_duration"] = "30-45 minutes" 
            schedule["weekly_goals"] = {"concepts": 3, "practice_problems": 5}
        else:
            schedule["sessions_per_week"] = 3
            schedule["session_duration"] = "45 minutes"
            schedule["weekly_goals"] = {"concepts": 4, "practice_problems": 7}
        
        # Recommend best study times (this would ideally use historical data)
        if profile.active_vs_passive > 0.6:
            schedule["best_times"] = ["Morning (9-11 AM)", "Afternoon (2-4 PM)"]
        else:
            schedule["best_times"] = ["Evening (6-8 PM)", "Late morning (10-12 PM)"]
        
        return schedule


# Global recommendation engine instance
recommendation_engine = RecommendationEngine()