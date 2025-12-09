from typing import List, Dict , cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from groq.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from ..config import settings, get_groq_client
from ..models import LearnerProfile
from ..database import get_db
from ..schemas import SessionCognitiveState , ChatRequest , ChatResponse

import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util


router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)


def make_message(role: str, content: str) -> ChatCompletionMessageParam:
    return cast(ChatCompletionMessageParam, {"role": role, "content": content})


def call_groq_chat(messages: List[ChatCompletionMessageParam]) -> str:
    client = get_groq_client()
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=messages,
        temperature=0.4,
        max_tokens=512
    )
    content = response.choices[0].message.content
    return content if content is not None else ""


def map_learner_to_session_profile(lp: LearnerProfile) -> SessionCognitiveState:
    if str(lp.sequential_global) == "Sequential":
        instruction_flow = "step_by_step"
    else:
        instruction_flow = "high_level"

    if str(lp.sensing_intuitive) == "Sensing":
        complexity_tolerance = "medium"
    else:
        complexity_tolerance = "high"

    if str(lp.active_reflective) == "Active":
        pace_preference = "fast"
    else:
        pace_preference = "slow"

    if str(lp.visual_verbal) == "Visual":
        input_preference = "example_first"
    else:
        input_preference = "theory_first"

    return SessionCognitiveState(
        instruction_flow=instruction_flow,
        complexity_tolerance=complexity_tolerance,
        pace_preference=pace_preference,
        input_preference=input_preference,
        engagement=None,
        confidence=1.0
    )



def build_system_prompt(lp: LearnerProfile, session_state: SessionCognitiveState) -> str:
    ils_desc = (
        f"The student is generally a {lp.active_reflective}, "
        f"{lp.sensing_intuitive}, {lp.visual_verbal}, {lp.sequential_global} learner."
    )

    session_desc = (
        f"Current session preferences:\n"
        f"- Instruction flow: {session_state.instruction_flow}\n"
        f"- Complexity tolerance: {session_state.complexity_tolerance}\n"
        f"- Pace preference: {session_state.pace_preference}\n"
        f"- Input preference: {session_state.input_preference}\n"
    )

    if session_state.engagement is not None:
        session_desc += f"- Engagement: {session_state.engagement}\n"

    tutor_instructions = (
        "You are an expert AI tutor specialized in **Operating Systems** for computer science students. Your knowledge covers the following comprehensive curriculum in detail:\n"
        "\n"
        "**Unit 1: Introduction to Operating Systems**\n"
        "1. What is an Operating System?\n"
        "2. Objectives and Functions of an OS\n"
        "3. Types of Operating Systems\n"
        "4. System Components and Structure\n"
        "5. OS Architecture (Monolithic, Layered, Microkernel)\n"
        "\n"
        "**Unit 2: Process Management**\n"
        "1. Process Concept and Process States\n"
        "2. Process Control Block (PCB)\n"
        "3. CPU Scheduling Algorithms (FCFS, SJF, RR, Priority)\n"
        "4. Interprocess Communication (IPC)\n"
        "5. Threads and Multithreading\n"
        "\n"
        "**Unit 3: Memory Management**\n"
        "1. Address Binding and Memory Allocation\n"
        "2. Contiguous Memory Allocation\n"
        "3. Paging and Segmentation\n"
        "4. Virtual Memory and Demand Paging\n"
        "5. Page Replacement Algorithms\n"
        "\n"
        "**Unit 4: File Systems and Storage Management**\n"
        "1. File Concepts and Access Methods\n"
        "2. Directory Structures\n"
        "3. Disk Scheduling Algorithms (FCFS, SSTF, SCAN, C-SCAN)\n"
        "4. File System Implementation\n"
        "5. Disk Management and RAID\n"
        "\n"
        "**Unit 5: Deadlocks and Synchronization**\n"
        "1. Deadlock Conditions and Resource Allocation Graph\n"
        "2. Deadlock Prevention, Avoidance, and Detection\n"
        "3. Banker’s Algorithm\n"
        "4. Process Synchronization and Semaphores\n"
        "5. Classical Synchronization Problems (Producer-Consumer, Readers-Writers, Dining Philosophers)\n"
        "\n"
        "Explain concepts clearly, adapt your teaching style to the student's profile, and use their specific preferences:\n"
        "- If step_by_step: break explanations into small ordered steps.\n"
        "- If high_level: give an overview first, then details.\n"
        "- If example_first: start with examples or code, then explain theory.\n"
        "- If theory_first: define concepts first, then show examples.\n"
        "- Adjust complexity and pace according to the preferences.\n"
        "Ask short follow-up questions when helpful and keep the tone supportive and concise."
    )

    return ils_desc + "\n\n" + session_desc + "\n" + tutor_instructions

@router.post("/vapi")
def vapi_webhook(payload: ChatRequest, db: Session = Depends(get_db)):
    return chat_conversation(payload, db)


@router.post("/test")
def test_chat(message: str):
    msgs = [
        make_message("system", "You are a helpful AI tutor."),
        make_message("user", message)
    ]
    reply = call_groq_chat(msgs)
    return {"reply": reply}


class CognitiveAnalyzer:
    def __init__(self):
        self.encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        self.dimensions = {
            "instruction_flow": [
                "step_by_step",
                "guided",
                "exploratory",
                "high_level"
            ],
            "complexity_tolerance": [
                "low",
                "medium",
                "high"
            ],
            "pace_preference": [
                "slow",
                "moderate",
                "fast"
            ],
            "input_preference": [
                "example_first",
                "theory_first",
                "analogy_based"
            ],
            "engagement": [
                "low",
                "medium",
                "high"
            ]
        }

        self.label_embeddings = {
            dim: {
                label: self.encoder.encode(label, convert_to_tensor=True)
                for label in labels
            }
            for dim, labels in self.dimensions.items()
        }

    def analyze(self, text: str) -> SessionCognitiveState:
        emb = self.encoder.encode(text, convert_to_tensor=True)

        chosen = {}
        confidence_scores = []

        for dim, labels in self.dimensions.items():
            sims = {
                label: util.cos_sim(emb, label_emb).item()
                for label, label_emb in self.label_embeddings[dim].items()
            }

            best_label = max(sims.keys(), key=lambda k: sims[k])
            best_conf = sims[best_label]

            chosen[dim] = best_label
            confidence_scores.append(best_conf)

        return SessionCognitiveState(
            instruction_flow=chosen["instruction_flow"],
            complexity_tolerance=chosen["complexity_tolerance"],
            pace_preference=chosen["pace_preference"],
            input_preference=chosen["input_preference"],
            engagement=chosen["engagement"],
            confidence=float(np.mean(confidence_scores))
        )


cognitive_analyzer = CognitiveAnalyzer()


@router.post("/conversation", response_model=ChatResponse)
def chat_conversation(payload: ChatRequest, db: Session = Depends(get_db)):
    lp = db.query(LearnerProfile).filter(LearnerProfile.user_id == payload.user_id).first()
    if lp is None:
        raise HTTPException(status_code=404, detail="Learner profile not found for this user.")

    baseline_state = map_learner_to_session_profile(lp)
    dynamic_state = cognitive_analyzer.analyze(payload.message)

    conf = dynamic_state.confidence
    threshold = 0.35

    def choose(baseline, dynamic):
        return dynamic if conf >= threshold else baseline

    final_state = SessionCognitiveState(
        instruction_flow = choose(baseline_state.instruction_flow, dynamic_state.instruction_flow),
        complexity_tolerance = choose(baseline_state.complexity_tolerance, dynamic_state.complexity_tolerance),
        pace_preference = choose(baseline_state.pace_preference, dynamic_state.pace_preference),
        input_preference = choose(baseline_state.input_preference, dynamic_state.input_preference),
        engagement = dynamic_state.engagement if conf >= threshold else baseline_state.engagement,
        confidence = conf
    )

    system_prompt = build_system_prompt(lp, final_state)

    messages: List[ChatCompletionMessageParam] = [
        make_message("system", system_prompt)
    ]

    for item in payload.history:
        messages.append(make_message(item.role, item.content))

    messages.append(make_message("user", payload.message))

    reply = call_groq_chat(messages)

    return ChatResponse(
        reply=reply,
        session_state=final_state
    )

