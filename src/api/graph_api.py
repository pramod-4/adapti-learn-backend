
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import List, Dict, Optional
from ..knowledge_graph.retriever import KnowledgeGraphRetriever
from ..knowledge_graph.schema import NodeLabel, RelationshipType
from ..logger import logger

router = APIRouter(prefix="/graph", tags=["DSA Knowledge Graph"])

def get_retriever() -> KnowledgeGraphRetriever:
    """Dependency to get retriever instance"""
    from ..main import retriever
    if not retriever:
        raise HTTPException(status_code=503, detail="Database connection not available")
    return retriever

@router.get("/search", summary="Search nodes in the DSA knowledge graph")
async def search_nodes(
    name: Optional[str] = Query(None, description="Search by node name (partial match)"),
    label: Optional[NodeLabel] = Query(None, description="Filter by node type"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty level"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results to return"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """
    Search for DSA concepts, topics, subtopics, or levels.
    Supports partial name matching and filtering by type and difficulty.
    """
    try:
        results = retriever.search_nodes(name=name, label=label, difficulty=difficulty, limit=limit)
        return {
            "query": {
                "name": name,
                "label": label.value if label else None,
                "difficulty": difficulty,
                "limit": limit
            },
            "count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Error searching nodes: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/node/{name}", summary="Get detailed information about a specific node")
async def get_node_details(
    name: str = Path(..., description="Exact node name"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Get complete details of a specific DSA concept by exact name."""
    try:
        result = retriever.get_node_details(name)
        if not result:
            raise HTTPException(status_code=404, detail=f"Node '{name}' not found")
        
        return {
            "node": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting node details for {name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get node details: {str(e)}")

@router.get("/topic/{name}/subtopics", summary="Get topic with its subtopics")
async def get_topic_with_subtopics(
    name: str = Path(..., description="Topic name (partial match)"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Get a topic along with all its subtopics."""
    try:
        result = retriever.get_topic_with_subtopics(name)
        if not result:
            raise HTTPException(status_code=404, detail=f"Topic containing '{name}' not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting topic {name} with subtopics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get topic details: {str(e)}")

@router.get("/prerequisites/{name}", summary="Get prerequisites for a concept")
async def get_prerequisites(
    name: str = Path(..., description="Node name (partial match)"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Get all prerequisites needed before learning this concept."""
    try:
        result = retriever.get_prerequisites(name)
        if not result["node"]:
            raise HTTPException(status_code=404, detail=f"Node containing '{name}' not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prerequisites for {name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get prerequisites: {str(e)}")

@router.get("/dependents/{name}", summary="Get what depends on this concept")
async def get_dependents(
    name: str = Path(..., description="Node name (partial match)"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Get all concepts that depend on (require) this concept as a prerequisite."""
    try:
        result = retriever.get_dependents(name)
        if not result["node"]:
            raise HTTPException(status_code=404, detail=f"Node containing '{name}' not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dependents for {name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dependents: {str(e)}")

@router.get("/learning-path", summary="Find learning path between concepts")
async def get_learning_path(
    start: str = Query(..., description="Starting concept name"),
    end: str = Query(..., description="Target concept name"),
    max_depth: int = Query(8, ge=1, le=15, description="Maximum path length to search"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Find the shortest learning path from one concept to another."""
    try:
        result = retriever.get_learning_path(start, end, max_depth)
        
        if result["path_length"] == 0 and result["message"] != "Path found successfully":
            if not result["start_node"] or not result["end_node"]:
                raise HTTPException(status_code=404, detail=result["message"])
            else:
                raise HTTPException(status_code=404, detail=f"No learning path found from '{start}' to '{end}'")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding learning path from {start} to {end}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to find learning path: {str(e)}")

@router.get("/similar-difficulty/{name}", summary="Find concepts with similar difficulty")
async def get_similar_difficulty(
    name: str = Path(..., description="Node name (partial match)"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Find other concepts with the same difficulty level."""
    try:
        result = retriever.get_related_by_difficulty(name)
        if not result["node"]:
            raise HTTPException(status_code=404, detail=f"Node containing '{name}' not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting similar difficulty for {name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get similar concepts: {str(e)}")

# Convenience endpoints
@router.get("/topics", summary="Get all topics")
async def get_all_topics(
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Get all available topics in the DSA knowledge graph."""
    try:
        results = retriever.search_nodes(label=NodeLabel.TOPIC, limit=limit)
        return {
            "count": len(results),
            "topics": results
        }
    except Exception as e:
        logger.error(f"Error getting all topics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get topics: {str(e)}")

@router.get("/levels", summary="Get all difficulty levels")
async def get_all_levels(
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Get all difficulty levels available in the system."""
    try:
        levels = retriever.get_all_levels()
        return {
            "count": len(levels),
            "levels": levels
        }
    except Exception as e:
        logger.error(f"Error getting all levels: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get levels: {str(e)}")

@router.get("/subtopics", summary="Get all subtopics")
async def get_all_subtopics(
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    retriever: KnowledgeGraphRetriever = Depends(get_retriever)
):
    """Get all available subtopics."""
    try:
        results = retriever.search_nodes(label=NodeLabel.SUBTOPIC, limit=limit)
        return {
            "count": len(results),
            "subtopics": results
        }
    except Exception as e:
        logger.error(f"Error getting all subtopics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get subtopics: {str(e)}")