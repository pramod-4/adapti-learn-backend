from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from .schema import NodeLabel, RelationshipType
from ..config import settings
from ..logger import logger
from typing import List, Dict, Optional, Any, Union

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

    # Core search function - handles most use cases
    def search_nodes(self, 
                    name: Optional[str] = None,
                    label: Optional[NodeLabel] = None,
                    properties: Optional[Dict] = None,
                    limit: int = 10) -> List[Dict]:
        """Universal search function for nodes"""
        conditions = []
        params = {"limit": limit}
        
        # Build dynamic query based on parameters
        if label:
            node_pattern = f"(n:{label})"
        else:
            node_pattern = "(n)"
            
        if name:
            conditions.append("toLower(n.name) CONTAINS toLower($name)")
            params["name"] = name
            
        if properties:
            for key, value in properties.items():
                conditions.append(f"n.{key} = ${key}")
                params[key] = value
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
        MATCH {node_pattern}
        {where_clause}
        RETURN n
        LIMIT $limit
        """
        
        results = self._execute_query(query, params)
        return [dict(record["n"]) for record in results]

    # Get node with its immediate relationships
    def get_node_context(self, node_name: str, depth: int = 1) -> Dict:
        """Get node with its relationships - covers most relationship queries"""
        query = f"""
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower($node_name)
        OPTIONAL MATCH (n)-[r*1..{depth}]-(connected)
        RETURN n, 
               collect(DISTINCT connected) as connected_nodes,
               collect(DISTINCT type(r[0])) as relationship_types
        LIMIT 1
        """
        
        results = self._execute_query(query, {"node_name": node_name})
        if results:
            record = results[0]
            return {
                "node": dict(record["n"]) if record["n"] else None,
                "connected_nodes": [dict(node) for node in record["connected_nodes"] if node],
                "relationship_types": [rel for rel in record["relationship_types"] if rel]
            }
        return {"node": None, "connected_nodes": [], "relationship_types": []}

    # Learning path - essential for educational app
    def get_learning_path(self, start_node: str, end_node: str, max_depth: int = 5) -> List[Dict]:
        """Get shortest learning path between nodes"""
        query = f"""
        MATCH (start), (end)
        WHERE toLower(start.name) CONTAINS toLower($start_node)
        AND toLower(end.name) CONTAINS toLower($end_node)
        
        MATCH path = shortestPath(
            (start)-[r:PREREQUISITE_FOR*1..{max_depth}]->(end)
        )
        RETURN [node in nodes(path) | node] as path_nodes
        """
        
        results = self._execute_query(query, {
            "start_node": start_node, 
            "end_node": end_node
        })
        
        if results and results[0]["path_nodes"]:
            return [dict(node) for node in results[0]["path_nodes"]]
        return []

    # Flexible relationship query
    def get_related_nodes(self, node_name: str, relationship: Optional[RelationshipType] = None) -> Dict:
        """Get nodes related by specific relationship type"""
        if relationship:
            rel_pattern = f"[r:{relationship}]"
        else:
            rel_pattern = "[r]"
            
        query = f"""
        MATCH (n)-{rel_pattern}-(related)
        WHERE toLower(n.name) CONTAINS toLower($node_name)
        RETURN n,
               collect(DISTINCT related) as related_nodes,
               collect(DISTINCT type(r)) as relationship_types
        """
        
        results = self._execute_query(query, {"node_name": node_name})
        if results:
            record = results[0]
            return {
                "node": dict(record["n"]) if record["n"] else None,
                "related_nodes": [dict(node) for node in record["related_nodes"] if node],
                "relationship_types": record["relationship_types"]
            }
        return {"node": None, "related_nodes": [], "relationship_types": []}
