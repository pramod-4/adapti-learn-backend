
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncio
from dataclasses import asdict

from src.entities.profile import CognitiveProfile, ProfileUpdate
from src.database.postgres import postgres_repo
from src.database.core import db_manager
from src.exceptions import CognitiveAnalysisError
from src.logger import logger


class InteractionMetrics:
    """Metrics extracted from user interactions"""
    
    def __init__(self, query: str, response_time: Optional[float] = None, 
                 domain: Optional[str] = None):
        self.query = query.lower()
        self.query_length = len(query.split())
        self.response_time = response_time
        self.domain = domain
        self.timestamp = datetime.utcnow()
        
        # Analyze query characteristics
        self.has_question_words = self._has_question_words()
        self.has_detail_indicators = self._has_detail_indicators()
        self.has_brevity_indicators = self._has_brevity_indicators()
        self.complexity_score = self._calculate_complexity()
    
    def _has_question_words(self) -> bool:
        """Check for active learning question words"""
        active_words = ['how', 'why', 'what if', 'compare', 'difference', 
                       'analyze', 'evaluate', 'explain difference', 'versus']
        return any(word in self.query for word in active_words)
    
    def _has_detail_indicators(self) -> bool:
        """Check for detailed explanation requests"""
        detail_words = ['detailed', 'step by step', 'in depth', 'comprehensive', 
                       'thorough', 'complete', 'full explanation', 'deep dive']
        return any(word in self.query for word in detail_words)
    
    def _has_brevity_indicators(self) -> bool:
        """Check for brief explanation requests"""
        brief_words = ['brief', 'summary', 'overview', 'quick', 'simple', 
                      'short', 'concise', 'tldr']
        return any(word in self.query for word in brief_words)
    
    def _calculate_complexity(self) -> float:
        """Calculate query complexity score (0-1)"""
        complexity = 0.0
        
        # Length factor
        if self.query_length > 15:
            complexity += 0.3
        elif self.query_length > 8:
            complexity += 0.2
        
        # Technical terms
        technical_terms = ['algorithm', 'implementation', 'optimization', 
                          'complexity', 'architecture', 'protocol']
        complexity += 0.1 * sum(1 for term in technical_terms if term in self.query)
        
        # Question depth
        if any(phrase in self.query for phrase in ['how does', 'why does', 'what happens']):
            complexity += 0.2
        
        return min(1.0, complexity)


class CognitiveAnalyzer:
    """Cognitive behavior analyzer for student profiling"""
    
    def __init__(self):
        self.learning_rate = 0.15  # How quickly profiles adapt
        self.confidence_increment = 0.05  # Confidence increase per interaction
    
    async def analyze_interaction(self, user_id: str, query: str, 
                                response_time: Optional[float] = None,
                                domain: Optional[str] = None,
                                session_metadata: Optional[Dict[str, Any]] = None) -> CognitiveProfile:
        """Analyze user interaction and update cognitive profile"""
        
        try:
            # Extract metrics from interaction
            metrics = InteractionMetrics(query, response_time, domain)
            
            # Get current profile or create new one
            current_profile = await postgres_repo.get_cognitive_profile(user_id)
            if not current_profile:
                current_profile = CognitiveProfile()
                await postgres_repo.create_cognitive_profile(user_id, current_profile)
            
            # Analyze cognitive dimensions
            dimension_updates = await self._analyze_dimensions(metrics, session_metadata)
            
            # Update profile with exponential moving average
            updated_profile = await self._update_profile(current_profile, dimension_updates)
            
            # Save updated profile
            await postgres_repo.update_cognitive_profile(user_id, updated_profile)
            
            # Cache updated profile
            await self._cache_profile(user_id, updated_profile)
            
            logger.info(f"Cognitive profile updated for user {user_id}")
            return updated_profile
            
        except Exception as e:
            logger.error(f"Cognitive analysis failed for user {user_id}: {e}")
            raise CognitiveAnalysisError(f"Analysis failed: {e}")
    
    async def _analyze_dimensions(self, metrics: InteractionMetrics, 
                                session_data: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Analyze cognitive dimensions from interaction metrics"""
        
        updates = {}
        
        # Active vs Passive Learning
        active_score = 0.5  # baseline
        if metrics.has_question_words:
            active_score += 0.3
        if metrics.complexity_score > 0.5:
            active_score += 0.2
        if metrics.query_length > 10:  # longer queries suggest engagement
            active_score += 0.1
        
        updates['active_vs_passive'] = min(1.0, active_score)
        
        # Fast vs Slow Learning
        speed_score = 0.5
        if metrics.response_time:
            # Normalize response time (assuming 30 seconds is average)
            normalized_time = min(1.0, metrics.response_time / 30.0)
            speed_score = 1.0 - normalized_time  # faster time = higher score
        
        updates['fast_vs_slow'] = speed_score
        
        # Overview vs Detailed Preference  
        detail_score = 0.5
        if metrics.has_detail_indicators:
            detail_score += 0.4
        elif metrics.has_brevity_indicators:
            detail_score -= 0.3
        
        # Query length as indicator
        if metrics.query_length > 15:
            detail_score += 0.2
        elif metrics.query_length < 5:
            detail_score -= 0.1
        
        updates['overview_vs_detailed'] = max(0.0, min(1.0, detail_score))
        
        # Long vs Short Response Preference
        # Initially correlate with detail preference, can be refined with feedback
        updates['long_vs_short'] = updates['overview_vs_detailed']
        
        return updates
    
    async def _update_profile(self, current: CognitiveProfile, 
                            updates: Dict[str, float]) -> CognitiveProfile:
        """Update profile using exponential moving average"""
        
        # Create updated profile
        updated = CognitiveProfile(**current.dict())
        
        # Apply exponential moving average
        for dimension, new_value in updates.items():
            if hasattr(updated, dimension):
                current_value = getattr(updated, dimension)
                smoothed_value = (
                    (1 - self.learning_rate) * current_value + 
                    self.learning_rate * new_value
                )
                setattr(updated, dimension, smoothed_value)
        
        # Update metadata
        updated.interaction_count += 1
        updated.confidence = min(1.0, updated.confidence + self.confidence_increment)
        updated.last_updated = datetime.utcnow()
        
        return updated
    
    async def _cache_profile(self, user_id: str, profile: CognitiveProfile):
        """Cache profile in Redis for fast access"""
        try:
            cache_key = f"cognitive_profile:{user_id}"
            profile_data = profile.json()
            await db_manager.redis.setex(cache_key, 3600, profile_data)  # 1 hour TTL
        except Exception as e:
            logger.warning(f"Failed to cache profile for user {user_id}: {e}")
    
    async def get_cached_profile(self, user_id: str) -> Optional[CognitiveProfile]:
        """Get cached cognitive profile"""
        try:
            cache_key = f"cognitive_profile:{user_id}"
            cached_data = await db_manager.redis.get(cache_key)
            if cached_data:
                return CognitiveProfile.parse_raw(cached_data)
        except Exception as e:
            logger.warning(f"Failed to get cached profile for user {user_id}: {e}")
        
        return None
    
    async def get_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user learning analytics"""
        try:
            # This would typically involve complex queries and analysis
            # For now, return basic analytics structure
            
            profile = await postgres_repo.get_cognitive_profile(user_id)
            if not profile:
                return {}
            
            return {
                "profile_summary": {
                    "learning_style": self._classify_learning_style(profile),
                    "confidence": profile.confidence,
                    "interactions": profile.interaction_count
                },
                "trends": {
                    "activity_level": "increasing" if profile.active_vs_passive > 0.6 else "stable",
                    "engagement": "high" if profile.confidence > 0.7 else "medium"
                },
                "recommendations": await self._generate_recommendations(profile)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate analytics for user {user_id}: {e}")
            return {}
    
    def _classify_learning_style(self, profile: CognitiveProfile) -> str:
        """Classify learning style based on profile"""
        if profile.active_vs_passive > 0.6 and profile.overview_vs_detailed > 0.6:
            return "Active Detailed Learner"
        elif profile.active_vs_passive > 0.6 and profile.overview_vs_detailed < 0.4:
            return "Active Overview Learner"
        elif profile.active_vs_passive < 0.4 and profile.overview_vs_detailed > 0.6:
            return "Passive Detailed Learner"
        else:
            return "Passive Overview Learner"
    
    async def _generate_recommendations(self, profile: CognitiveProfile) -> List[str]:
        """Generate learning recommendations based on profile"""
        recommendations = []
        
        if profile.active_vs_passive < 0.4:
            recommendations.append("Try asking more 'how' and 'why' questions to engage deeper with concepts")
        
        if profile.fast_vs_slow > 0.8:
            recommendations.append("Consider exploring advanced topics or additional challenges")
        elif profile.fast_vs_slow < 0.3:
            recommendations.append("Take your time with concepts - consider reviewing prerequisites")
        
        if profile.confidence < 0.3:
            recommendations.append("Start with easier concepts to build confidence")
        
        return recommendations


# Global cognitive analyzer instance
cognitive_analyzer = CognitiveAnalyzer()