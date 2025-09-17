
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import asyncio

from src.entities.user import User
from src.entities.profile import CognitiveProfile
from src.database.postgres import postgres_repo
from src.database.core import db_manager
from src.exceptions import DatabaseError
from src.logger import logger


@dataclass
class InteractionFeedback:
    """User feedback on system responses"""
    interaction_id: str
    user_id: str
    rating: int  # 1-5 scale
    feedback_type: str  # helpful, too_complex, too_simple, inaccurate, etc.
    comments: Optional[str] = None
    timestamp: datetime = datetime.utcnow()


@dataclass
class LearningProgress:
    """Learning progress tracking"""
    user_id: str
    domain: str
    concept_id: str
    mastery_level: float  # 0-1 scale
    time_spent: int  # seconds
    attempts: int
    last_interaction: datetime
    progress_trend: str  # improving, stable, declining


class FeedbackTracker:
    """Tracks user feedback and learning progress"""
    
    def __init__(self):
        self.feedback_cache = {}  # In-memory cache for recent feedback
    
    async def record_interaction_feedback(self, feedback: InteractionFeedback) -> bool:
        """Record user feedback on system response"""
        try:
            async with db_manager.get_postgres_connection() as conn:
                await conn.execute("""
                    INSERT INTO interaction_feedback 
                    (interaction_id, user_id, rating, feedback_type, comments, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, feedback.interaction_id, feedback.user_id, feedback.rating, 
                    feedback.feedback_type, feedback.comments, feedback.timestamp)
            
            # Cache recent feedback for analysis
            cache_key = f"feedback:{feedback.user_id}"
            if cache_key not in self.feedback_cache:
                self.feedback_cache[cache_key] = []
            self.feedback_cache[cache_key].append(feedback)
            
            # Keep only recent feedback in cache (last 10 interactions)
            self.feedback_cache[cache_key] = self.feedback_cache[cache_key][-10:]
            
            # Trigger adaptive analysis if feedback indicates issues
            if feedback.rating <= 2:  # Poor rating
                await self._analyze_negative_feedback(feedback)
            
            logger.info(f"Feedback recorded for user {feedback.user_id}: {feedback.rating}/5")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")
            return False
    
    async def track_learning_progress(self, user_id: str, domain: str, 
                                    concept_id: str, interaction_time: int,
                                    success_indicators: Dict[str, Any]) -> LearningProgress:
        """Track learning progress for a concept"""
        try:
            # Calculate mastery level based on various indicators
            mastery_level = await self._calculate_mastery_level(
                user_id, concept_id, success_indicators
            )
            
            async with db_manager.get_postgres_connection() as conn:
                # Get existing progress or create new
                existing = await conn.fetchrow("""
                    SELECT * FROM learning_progress 
                    WHERE user_id = $1 AND concept_id = $2
                """, user_id, concept_id)
                
                if existing:
                    # Update existing progress
                    new_attempts = existing['attempts'] + 1
                    new_time = existing['time_spent'] + interaction_time
                    
                    # Calculate progress trend
                    trend = self._calculate_trend(existing['mastery_level'], mastery_level)
                    
                    await conn.execute("""
                        UPDATE learning_progress SET
                            mastery_level = $3,
                            time_spent = $4,
                            attempts = $5,
                            progress_trend = $6,
                            last_interaction = $7,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = $1 AND concept_id = $2
                    """, user_id, concept_id, mastery_level, new_time, 
                        new_attempts, trend, datetime.utcnow())
                    
                    progress = LearningProgress(
                        user_id=user_id,
                        domain=domain,
                        concept_id=concept_id,
                        mastery_level=mastery_level,
                        time_spent=new_time,
                        attempts=new_attempts,
                        last_interaction=datetime.utcnow(),
                        progress_trend=trend
                    )
                else:
                    # Create new progress record
                    await conn.execute("""
                        INSERT INTO learning_progress 
                        (user_id, domain, concept_id, mastery_level, time_spent, 
                         attempts, progress_trend, last_interaction, created_at)
                        VALUES ($1, $2, $3, $4, $5, 1, 'improving', $6, CURRENT_TIMESTAMP)
                    """, user_id, domain, concept_id, mastery_level, interaction_time, 
                        datetime.utcnow())
                    
                    progress = LearningProgress(
                        user_id=user_id,
                        domain=domain,
                        concept_id=concept_id,
                        mastery_level=mastery_level,
                        time_spent=interaction_time,
                        attempts=1,
                        last_interaction=datetime.utcnow(),
                        progress_trend='improving'
                    )
            
            return progress
            
        except Exception as e:
            logger.error(f"Failed to track progress for user {user_id}: {e}")
            raise DatabaseError(f"Progress tracking failed: {e}")
    
    async def get_user_progress_summary(self, user_id: str, 
                                      days: int = 30) -> Dict[str, Any]:
        """Get comprehensive progress summary for user"""
        try:
            async with db_manager.get_postgres_connection() as conn:
                # Get progress across all domains
                progress_data = await conn.fetch("""
                    SELECT domain, concept_id, mastery_level, time_spent, 
                           attempts, progress_trend, last_interaction
                    FROM learning_progress
                    WHERE user_id = $1 
                      AND last_interaction >= $2
                    ORDER BY last_interaction DESC
                """, user_id, datetime.utcnow() - timedelta(days=days))
                
                # Get feedback summary
                feedback_data = await conn.fetch("""
                    SELECT rating, feedback_type, created_at
                    FROM interaction_feedback
                    WHERE user_id = $1 
                      AND created_at >= $2
                    ORDER BY created_at DESC
                """, user_id, datetime.utcnow() - timedelta(days=days))
                
                # Calculate summary metrics
                summary = await self._calculate_progress_summary(progress_data, feedback_data)
                
                return summary
                
        except Exception as e:
            logger.error(f"Failed to get progress summary for user {user_id}: {e}")
            return {}
    
    async def _calculate_mastery_level(self, user_id: str, concept_id: str, 
                                     indicators: Dict[str, Any]) -> float:
        """Calculate mastery level based on success indicators"""
        mastery = 0.5  # baseline
        
        # Response time indicator
        if 'response_time' in indicators:
            response_time = indicators['response_time']
            if response_time < 15:  # Quick response suggests confidence
                mastery += 0.2
            elif response_time > 60:  # Slow response suggests difficulty
                mastery -= 0.1
        
        # Question complexity handled successfully
        if indicators.get('handled_complex_question', False):
            mastery += 0.2
        
        # Follow-up questions asked (shows engagement)
        follow_ups = indicators.get('follow_up_questions', 0)
        mastery += min(0.1, follow_ups * 0.05)
        
        # Previous interactions with this concept
        # (This would require additional database queries)
        
        return max(0.0, min(1.0, mastery))
    
    def _calculate_trend(self, old_mastery: float, new_mastery: float) -> str:
        """Calculate progress trend"""
        diff = new_mastery - old_mastery
        
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining" 
        else:
            return "stable"
    
    async def _calculate_progress_summary(self, progress_data: List, 
                                        feedback_data: List) -> Dict[str, Any]:
        """Calculate comprehensive progress summary"""
        if not progress_data:
            return {"message": "No recent learning activity"}
        
        # Domain-wise progress
        domain_progress = {}
        for row in progress_data:
            domain = row['domain']
            if domain not in domain_progress:
                domain_progress[domain] = {
                    'concepts_studied': 0,
                    'total_time': 0,
                    'avg_mastery': 0.0,
                    'improving_concepts': 0
                }
            
            domain_progress[domain]['concepts_studied'] += 1
            domain_progress[domain]['total_time'] += row['time_spent']
            domain_progress[domain]['avg_mastery'] += row['mastery_level']
            
            if row['progress_trend'] == 'improving':
                domain_progress[domain]['improving_concepts'] += 1
        
        # Calculate averages
        for domain in domain_progress:
            concepts_count = domain_progress[domain]['concepts_studied']
            domain_progress[domain]['avg_mastery'] /= concepts_count
            domain_progress[domain]['avg_time_per_concept'] = (
                domain_progress[domain]['total_time'] / concepts_count / 60  # minutes
            )
        
        # Feedback analysis
        feedback_summary = {}
        if feedback_data:
            ratings = [row['rating'] for row in feedback_data]
            feedback_summary = {
                'avg_rating': sum(ratings) / len(ratings),
                'total_feedback': len(ratings),
                'positive_feedback': len([r for r in ratings if r >= 4]),
                'negative_feedback': len([r for r in ratings if r <= 2])
            }
        
        return {
            'domains': domain_progress,
            'feedback': feedback_summary,
            'overall_metrics': {
                'total_concepts': len(progress_data),
                'total_study_time': sum(row['time_spent'] for row in progress_data) / 60,  # minutes
                'avg_mastery': sum(row['mastery_level'] for row in progress_data) / len(progress_data),
                'active_days': len(set(row['last_interaction'].date() for row in progress_data))
            }
        }
    
    async def _analyze_negative_feedback(self, feedback: InteractionFeedback):
        """Analyze and respond to negative feedback"""
        logger.warning(f"Negative feedback received from user {feedback.user_id}: "
                      f"{feedback.feedback_type} - {feedback.comments}")
        
        # This could trigger:
        # 1. Cognitive profile adjustments
        # 2. Content difficulty recalibration  
        # 3. Alert to human instructors
        # 4. A/B test different response strategies
        
        # For now, just log and potentially adjust cognitive profile
        if feedback.feedback_type == "too_complex":
            # Signal that user might prefer simpler explanations
            pass
        elif feedback.feedback_type == "too_simple":
            # Signal that user might need more advanced content
            pass


# Global feedback tracker instance
feedback_tracker = FeedbackTracker()
