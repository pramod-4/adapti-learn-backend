
from typing import List, Optional, Dict, Any
from neo4j import AsyncResult

from src.database.core import db_manager
from src.entities.knowledge import (
    ConceptNode, ConceptRelation, LearningPath, 
    SearchQuery, SearchResult, Domain, ConceptDifficulty, RelationType
)
from src.exceptions import KnowledgeGraphError
from src.logger import logger


class Neo4jRepository:
    """Neo4j repository for knowledge graph operations"""
    
    async def create_constraints(self):
        """Create Neo4j constraints and indexes"""
        async with db_manager.get_neo4j_session() as session:
            # Create constraints
            await session.run("""
                CREATE CONSTRAINT concept_id_unique IF NOT EXISTS
                FOR (c:Concept) REQUIRE c.concept_id IS UNIQUE
            """)
            
            # Create indexes for better performance
            await session.run("CREATE INDEX concept_name_idx IF NOT EXISTS FOR (c:Concept) ON (c.concept_name)")
            await session.run("CREATE INDEX concept_domain_idx IF NOT EXISTS FOR (c:Concept) ON (c.domain)")
            await session.run("CREATE INDEX concept_difficulty_idx IF NOT EXISTS FOR (c:Concept) ON (c.difficulty_level)")
            
            logger.info("Neo4j constraints and indexes created")
    
    async def create_concept(self, concept: ConceptNode) -> ConceptNode:
        """Create a concept node"""
        async with db_manager.get_neo4j_session() as session:
            result = await session.run("""
                CREATE (c:Concept {
                    concept_id: $concept_id,
                    concept_name: $concept_name,
                    domain: $domain,
                    difficulty_level: $difficulty_level,
                    description: $description,
                    keywords: $keywords,
                    learning_objectives: $learning_objectives,
                    examples: $examples,
                    resources: $resources,
                    created_at: datetime(),
                    updated_at: datetime()
                })
                RETURN c
            """, **concept.dict())
            
            record = await result.single()
            if not record:
                raise KnowledgeGraphError(f"Failed to create concept: {concept.concept_id}")
            
            return concept
    
    async def get_concept(self, concept_id: str) -> Optional[ConceptNode]:
        """Get concept by ID"""
        async with db_manager.get_neo4j_session() as session:
            result = await session.run("""
                MATCH (c:Concept {concept_id: $concept_id})
                RETURN c
            """, concept_id=concept_id)
            
            record = await result.single()
            if record:
                node_data = dict(record["c"])
                # Convert datetime objects to strings if needed
                if 'created_at' in node_data:
                    node_data['created_at'] = node_data['created_at'].isoformat()
                return ConceptNode(**node_data)
            return None
    
    async def search_concepts(self, query: SearchQuery) -> List[SearchResult]:
        """Search concepts with filters"""
        async with db_manager.get_neo4j_session() as session:
            # Build dynamic Cypher query
            where_clauses = []
            parameters = {"query_text": query.query_text.lower()}
            
            if query.domain_filter:
                where_clauses.append("c.domain = $domain")
                parameters["domain"] = query.domain_filter.value
            
            if query.difficulty_filter:
                where_clauses.append("c.difficulty_level = $difficulty")
                parameters["difficulty"] = query.difficulty_filter.value
            
            where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
            cypher_query = f"""
                MATCH (c:Concept)
                {where_clause}
                WHERE toLower(c.concept_name) CONTAINS $query_text 
                   OR toLower(c.description) CONTAINS $query_text
                   OR ANY(keyword IN c.keywords WHERE toLower(keyword) CONTAINS $query_text)
                WITH c,
                     CASE 
                         WHEN toLower(c.concept_name) = $query_text THEN 1.0
                         WHEN toLower(c.concept_name) CONTAINS $query_text THEN 0.8
                         WHEN toLower(c.description) CONTAINS $query_text THEN 0.6
                         ELSE 0.4
                     END as relevance_score
                ORDER BY relevance_score DESC, c.difficulty_level ASC
                LIMIT $limit
                RETURN c, relevance_score
            """
            
            parameters["limit"] = query.limit
            result = await session.run(cypher_query, **parameters)
            
            search_results = []
            async for record in result:
                concept_data = dict(record["c"])
                concept = ConceptNode(**concept_data)
                
                # Get related concepts if requested
                related_concepts = []
                prerequisites = []
                
                if query.include_related:
                    related_concepts = await self._get_related_concepts(concept.concept_id, session)
                    prerequisites = await self._get_prerequisites(concept.concept_id, session)
                
                search_results.append(SearchResult(
                    concept=concept,
                    relevance_score=record["relevance_score"],
                    match_type="name" if concept.concept_name.lower() in query.query_text.lower() else "description",
                    related_concepts=related_concepts,
                    prerequisites=prerequisites
                ))
            
            return search_results
    
    async def create_relationship(self, relation: ConceptRelation) -> ConceptRelation:
        """Create relationship between concepts"""
        async with db_manager.get_neo4j_session() as session:
            await session.run("""
                MATCH (from:Concept {concept_id: $from_concept})
                MATCH (to:Concept {concept_id: $to_concept})
                CREATE (from)-[r:RELATES {
                    type: $relation_type,
                    weight: $weight,
                    metadata: $metadata,
                    created_at: datetime()
                }]->(to)
            """, **relation.dict())
            
            return relation
    
    async def get_prerequisites(self, concept_id: str) -> List[ConceptNode]:
        """Get prerequisite concepts"""
        async with db_manager.get_neo4j_session() as session:
            return await self._get_prerequisites(concept_id, session)
    
    async def _get_prerequisites(self, concept_id: str, session) -> List[ConceptNode]:
        """Internal method to get prerequisites"""
        result = await session.run("""
            MATCH (prereq:Concept)-[r:RELATES]->(c:Concept {concept_id: $concept_id})
            WHERE r.type = 'prerequisite_for' OR r.type = 'depends_on'
            RETURN prereq
            ORDER BY r.weight DESC
        """, concept_id=concept_id)
        
        prerequisites = []
        async for record in result:
            concept_data = dict(record["prereq"])
            prerequisites.append(ConceptNode(**concept_data))
        
        return prerequisites
    
    async def _get_related_concepts(self, concept_id: str, session) -> List[ConceptNode]:
        """Internal method to get related concepts"""
        result = await session.run("""
            MATCH (c:Concept {concept_id: $concept_id})-[r:RELATES]-(related:Concept)
            WHERE r.type IN ['related_to', 'part_of', 'example_of']
            RETURN related, r.weight as weight
            ORDER BY weight DESC
            LIMIT 5
        """, concept_id=concept_id)
        
        related = []
        async for record in result:
            concept_data = dict(record["related"])
            related.append(ConceptNode(**concept_data))
        
        return related
    
    async def get_learning_path(self, domain: Domain, target_level: ConceptDifficulty) -> Optional[LearningPath]:
        """Generate learning path for domain and difficulty level"""
        async with db_manager.get_neo4j_session() as session:
            # Find concepts in domain up to target level
            result = await session.run("""
                MATCH (c:Concept)
                WHERE c.domain = $domain AND c.difficulty_level <= $target_level
                WITH c
                MATCH path = (start:Concept)-[:RELATES*]->(end:Concept)
                WHERE start.difficulty_level = 1 
                  AND end.difficulty_level = $target_level
                  AND ALL(node IN nodes(path) WHERE node.domain = $domain)
                RETURN [node IN nodes(path) | node.concept_id] as concept_sequence
                ORDER BY length(path) ASC
                LIMIT 1
            """, domain=domain.value, target_level=target_level.value)
            
            record = await result.single()
            if record:
                return LearningPath(
                    path_id=f"{domain.value.lower()}_{target_level.value}",
                    path_name=f"{domain.value} Learning Path (Level {target_level.value})",
                    domain=domain,
                    target_level=target_level,
                    concept_sequence=record["concept_sequence"]
                )
            return None


# Global Neo4j repository instance
neo4j_repo = Neo4jRepository()
