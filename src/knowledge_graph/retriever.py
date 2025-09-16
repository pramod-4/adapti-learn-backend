# src/knowledge_graph/retriever.py
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from .schema import NodeLabel, RelationshipType
from ..config import settings
from ..logger import logger
from typing import List, Dict, Optional, Any

class KnowledgeGraphRetriever:
    def __init__(self):
        try:
            self.driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password)
            )
            self.driver.verify_connectivity()
            logger.info("Neo4j connection successful")
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        if self.driver:
            self.driver.close()
            logger.info("Neo4j driver closed")
    
    def _execute_query(self, query: str, parameters: Dict = None) -> List[Dict]:
        """Execute query with proper error handling"""
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Query execution failed: {query[:100]}... Error: {e}")
            raise

    def search_nodes(self, 
                    name: Optional[str] = None,
                    label: Optional[NodeLabel] = None,
                    difficulty: Optional[str] = None,
                    limit: int = 10) -> List[Dict]:
        """Universal search function for DSA nodes"""
        conditions = []
        params = {"limit": limit}
        
        # Build node pattern with label
        if label:
            node_pattern = f"(n:{label.value})"
        else:
            node_pattern = "(n)"
            
        # Add search conditions
        if name:
            conditions.append("toLower(n.name) CONTAINS toLower($name)")
            params["name"] = name
            
        if difficulty:
            conditions.append("toLower(n.difficulty) = toLower($difficulty)")
            params["difficulty"] = difficulty
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
        MATCH {node_pattern}
        {where_clause}
        RETURN n
        ORDER BY n.name
        LIMIT $limit
        """
        
        logger.info(f"Executing search query: {query} with params: {params}")
        results = self._execute_query(query, params)
        
        # Convert Neo4j nodes to dictionaries properly
        nodes = []
        for record in results:
            if record["n"]:
                node_dict = dict(record["n"])
                # Add labels for clarity
                node_dict["labels"] = list(record["n"].labels)
                nodes.append(node_dict)
        
        return nodes

    def get_node_details(self, node_name: str) -> Optional[Dict]:
        """Get detailed information about a specific node"""
        query = """
        MATCH (n)
        WHERE toLower(n.name) = toLower($node_name)
        RETURN n, labels(n) as node_labels
        LIMIT 1
        """
        
        logger.info(f"Getting node details for: {node_name}")
        results = self._execute_query(query, {"node_name": node_name})
        
        if results:
            record = results[0]
            if record["n"]:
                node_dict = dict(record["n"])
                node_dict["labels"] = record["node_labels"]
                return node_dict
        return None

    def get_topic_with_subtopics(self, topic_name: str) -> Optional[Dict]:
        """Get topic with its subtopics"""
        query = """
        MATCH (t:Topic)
        WHERE toLower(t.name) CONTAINS toLower($topic_name)
        OPTIONAL MATCH (t)-[:HAS_SUBTOPIC]->(s:Subtopic)
        RETURN t, collect(s) as subtopics
        """
        
        logger.info(f"Getting topic with subtopics: {topic_name}")
        results = self._execute_query(query, {"topic_name": topic_name})
        
        if results:
            record = results[0]
            if record["t"]:
                topic_dict = dict(record["t"])
                topic_dict["labels"] = ["Topic"]
                
                subtopics = []
                for subtopic in record["subtopics"]:
                    if subtopic:
                        subtopic_dict = dict(subtopic)
                        subtopic_dict["labels"] = ["Subtopic"]
                        subtopics.append(subtopic_dict)
                
                return {
                    "topic": topic_dict,
                    "subtopics": subtopics,
                    "subtopic_count": len(subtopics)
                }
        return None

    def get_prerequisites(self, node_name: str) -> Dict:
        """Get prerequisites for a topic/subtopic"""
        query = """
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower($node_name)
        OPTIONAL MATCH (prereq)-[:PREREQUISITE_FOR]->(n)
        RETURN n, collect(prereq) as prerequisites
        """
        
        logger.info(f"Getting prerequisites for: {node_name}")
        results = self._execute_query(query, {"node_name": node_name})
        
        if results:
            record = results[0]
            if record["n"]:
                node_dict = dict(record["n"])
                node_dict["labels"] = list(record["n"].labels)
                
                prerequisites = []
                for prereq in record["prerequisites"]:
                    if prereq:
                        prereq_dict = dict(prereq)
                        prereq_dict["labels"] = list(prereq.labels)
                        prerequisites.append(prereq_dict)
                
                return {
                    "node": node_dict,
                    "prerequisites": prerequisites,
                    "prerequisite_count": len(prerequisites)
                }
        
        return {"node": None, "prerequisites": [], "prerequisite_count": 0}

    def get_dependents(self, node_name: str) -> Dict:
        """Get what depends on this node (what this is a prerequisite for)"""
        query = """
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower($node_name)
        OPTIONAL MATCH (n)-[:PREREQUISITE_FOR]->(dependent)
        RETURN n, collect(dependent) as dependents
        """
        
        logger.info(f"Getting dependents for: {node_name}")
        results = self._execute_query(query, {"node_name": node_name})
        
        if results:
            record = results[0]
            if record["n"]:
                node_dict = dict(record["n"])
                node_dict["labels"] = list(record["n"].labels)
                
                dependents = []
                for dependent in record["dependents"]:
                    if dependent:
                        dependent_dict = dict(dependent)
                        dependent_dict["labels"] = list(dependent.labels)
                        dependents.append(dependent_dict)
                
                return {
                    "node": node_dict,
                    "dependents": dependents,
                    "dependent_count": len(dependents)
                }
        
        return {"node": None, "dependents": [], "dependent_count": 0}

    def get_learning_path(self, start_node: str, end_node: str, max_depth: int = 8) -> Dict:
        """Get shortest learning path using PREREQUISITE_FOR relationships"""
        # First, let's find if both nodes exist
        check_query = """
        MATCH (start), (end)
        WHERE toLower(start.name) CONTAINS toLower($start_node)
        AND toLower(end.name) CONTAINS toLower($end_node)
        RETURN start, end
        """
        
        check_results = self._execute_query(check_query, {
            "start_node": start_node,
            "end_node": end_node
        })
        
        if not check_results:
            return {
                "path": [],
                "path_length": 0,
                "start_node": None,
                "end_node": None,
                "message": "One or both nodes not found"
            }
        
        # Now find the shortest path
        path_query = f"""
        MATCH (start), (end)
        WHERE toLower(start.name) CONTAINS toLower($start_node)
        AND toLower(end.name) CONTAINS toLower($end_node)
        
        MATCH path = shortestPath((start)-[:PREREQUISITE_FOR*1..{max_depth}]->(end))
        RETURN path, length(path) as path_length
        """
        
        logger.info(f"Finding learning path from {start_node} to {end_node}")
        results = self._execute_query(path_query, {
            "start_node": start_node,
            "end_node": end_node
        })
        
        if results and results[0]["path"]:
            path_nodes = []
            for node in results[0]["path"].nodes:
                node_dict = dict(node)
                node_dict["labels"] = list(node.labels)
                path_nodes.append(node_dict)
            
            return {
                "path": path_nodes,
                "path_length": results[0]["path_length"],
                "start_node": dict(check_results[0]["start"]),
                "end_node": dict(check_results[0]["end"]),
                "message": "Path found successfully"
            }
        
        return {
            "path": [],
            "path_length": 0,
            "start_node": dict(check_results[0]["start"]),
            "end_node": dict(check_results[0]["end"]),
            "message": "No path found within depth limit"
        }

    def get_related_by_difficulty(self, node_name: str) -> Dict:
        """Get nodes with similar difficulty level"""
        query = """
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower($node_name)
        AND n.difficulty IS NOT NULL
        
        WITH n, n.difficulty as target_difficulty
        
        MATCH (similar)
        WHERE similar.difficulty = target_difficulty
        AND similar <> n
        
        RETURN n, collect(similar) as similar_nodes, target_difficulty
        """
        
        logger.info(f"Getting nodes with similar difficulty to: {node_name}")
        results = self._execute_query(query, {"node_name": node_name})
        
        if results:
            record = results[0]
            if record["n"]:
                node_dict = dict(record["n"])
                node_dict["labels"] = list(record["n"].labels)
                
                similar_nodes = []
                for similar in record["similar_nodes"]:
                    if similar:
                        similar_dict = dict(similar)
                        similar_dict["labels"] = list(similar.labels)
                        similar_nodes.append(similar_dict)
                
                return {
                    "node": node_dict,
                    "difficulty_level": record["target_difficulty"],
                    "similar_nodes": similar_nodes,
                    "similar_count": len(similar_nodes)
                }
        
        return {"node": None, "difficulty_level": None, "similar_nodes": [], "similar_count": 0}

    def get_all_levels(self) -> List[Dict]:
        """Get all difficulty levels in the system"""
        query = """
        MATCH (l:Level)
        RETURN l
        ORDER BY l.order
        """
        
        results = self._execute_query(query)
        levels = []
        for record in results:
            if record["l"]:
                level_dict = dict(record["l"])
                level_dict["labels"] = ["Level"]
                levels.append(level_dict)
        
        return levels
