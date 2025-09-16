# src/knowledge_graph/schema.py

"""
Schema definitions for the Knowledge Graph.
This includes node labels, relationship types, and property keys.
"""

from enum import Enum


class NodeLabel(str, Enum):
    LEVEL = "Level"
    TOPIC = "Topic"
    SUBTOPIC = "Subtopic"


class RelationshipType(str, Enum):
    PREREQUISITE_FOR = "PREREQUISITE_FOR"
    USED_IN = "USED_IN"
    CONTAINS = "CONTAINS"
    HAS_SUBTOPIC = "HAS_SUBTOPIC"
    USED_WITH = "USED_WITH"
    FREQUENTLY_TESTED_IN = "FREQUENTLY_TESTED_IN"
    EASIER_THAN = "EASIER_THAN"


class PropertyKey(str, Enum):
    DESCRIPTION = "description"
    DIFFICULTY = "difficulty"
    ESTIMATED_WEEKS = "estimated_weeks"
    ID = "id"
    NAME = "name"
    ORDER = "order"
    COMPLEXITY = "complexity"
    ESTIMATED_HOURS = "estimated_hours"
    LEVEL = "level"
    PRACTICAL_APPLICATIONS = "practical_applications"
    TYPE = "type"
    KEY_CONCEPTS = "key_concepts"
    PARENT_TOPIC = "parent_topic"
    SPACE_COMPLEXITY = "space_complexity"
    TIME_COMPLEXITY = "time_complexity"
    STRENGTH = "strength"
    DIFFICULTY_GAP = "difficulty_gap"
    DATA = "data"
    NODES = "nodes"
    RELATIONSHIPS = "relationships"
    STYLE = "style"
    VISUALISATION = "visualisation"
