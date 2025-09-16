
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Optional
from ..knowledge_graph.retriever import KnowledgeGraphRetriever
from ..knowledge_graph.schema import NodeLabel, RelationshipType
from ..logger import logger

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])

def get_retriever() -> KnowledgeGraphRetriever:
    """Dependency to get retriever instance"""
    from ..main import retriever
    if not retriever:
        raise HTTPException(status_code=503, detail="Database connection not available")
    return retriever

@router.get("/search")
async def search_nodes(
    name: Optional[str] = Query(None, description="Search by node name"),
    label: Optional[NodeLabel] = Query(None, description="Filter by node label"),
    limit: int = Query(10, description="Maximum results to return"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Universal search endpoint - handles most search needs"""
    try:
        results = retriever.search_nodes(name=name, label=label, limit=limit)
        return {
            "count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Error searching nodes: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@router.get("/node/{name}/context")
async def get_node_context(
    name: str, 
    depth: int = Query(1, description="Relationship depth to explore"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Get node with its relationships - replaces multiple specific endpoints"""
    try:
        result = retriever.get_node_context(name, depth)
        if not result["node"]:
            raise HTTPException(status_code=404, detail=f"Node not found: {name}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting node context for {name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get node context")

@router.get("/learning-path")
async def get_learning_path(
    start: str = Query(..., description="Starting topic/concept"),
    end: str = Query(..., description="Target topic/concept"),
    max_depth: int = Query(5, description="Maximum path length"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Get learning path between two concepts"""
    try:
        path = retriever.get_learning_path(start, end, max_depth)
        if not path:
            raise HTTPException(
                status_code=404, 
                detail=f"No learning path found from '{start}' to '{end}'"
            )
        return {
            "path_length": len(path),
            "path": path
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding path from {start} to {end}: {e}")
        raise HTTPException(status_code=500, detail="Failed to find learning path")

@router.get("/node/{name}/related")
async def get_related_nodes(
    name: str,
    relationship: Optional[RelationshipType] = Query(None, description="Filter by relationship type"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Get nodes related to the given node"""
    try:
        result = retriever.get_related_nodes(name, relationship)
        if not result["node"]:
            raise HTTPException(status_code=404, detail=f"Node not found: {name}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting related nodes for {name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get related nodes")

# Convenience endpoints for common use cases
@router.get("/topics")
async def get_all_topics(
    limit: int = Query(50, description="Maximum results"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Get all topics - common use case"""
    return await search_nodes(label=NodeLabel.TOPIC, limit=limit, retriever=retriever)

@router.get("/topic/{name}")
async def get_topic_details(
    name: str,
    include_subtopics: bool = Query(True, description="Include subtopics in response"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Get topic with optional subtopics - replaces topic-specific endpoints"""
    try:
        if include_subtopics:
            # Get topic with its subtopics using context
            result = retriever.get_related_nodes(name, RelationshipType.HAS_SUBTOPIC)
            if not result["node"]:
                raise HTTPException(status_code=404, detail=f"Topic not found: {name}")
            
            return {
                "topic": result["node"],
                "subtopics": result["related_nodes"]
            }
        else:
            # Just get the topic
            topics = retriever.search_nodes(name=name, label=NodeLabel.TOPIC, limit=1)
            if not topics:
                raise HTTPException(status_code=404, detail=f"Topic not found: {name}")
            return {"topic": topics[0]}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting topic {name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get topic details")