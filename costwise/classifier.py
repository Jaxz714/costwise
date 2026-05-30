"""Task complexity classifier using keyword/pattern matching."""

from __future__ import annotations

import re
from typing import Optional

from .models import TaskComplexity


# Keyword patterns for each complexity level
SIMPLE_PATTERNS = [
    r"\bsummarize\b", r"\bsummary\b", r"\bsum up\b",
    r"\btranslate\b", r"\btranslation\b",
    r"\bformat\b", r"\breformat\b",
    r"\blist\b", r"\blist out\b", r"\benumerate\b",
    r"\bwhat is\b", r"\bwhat are\b", r"\bwhat does\b",
    r"\bdefine\b", r"\bdefinition\b",
    r"\bconvert\b", r"\btransform\b",
    r"\bextract\b", r"\bpull out\b",
    r"\bfill in\b", r"\bcomplete\b",
    r"\brephrase\b", r"\breword\b",
    r"\bcapitalize\b", r"\blowercase\b", r"\buppercase\b",
    r"\bsort\b", r"\bfilter\b",
    r"\bcount\b", r"\btally\b",
    r"\bshorten\b", r"\bcondense\b",
    r"\bfix grammar\b", r"\bproofread\b",
    r"\btrim\b", r"\bclean up\b",
]

MEDIUM_PATTERNS = [
    r"\bexplain\b", r"\bexplanation\b", r"\bdescribe\b",
    r"\bcompare\b", r"\bcontrast\b", r"\bdifference\b",
    r"\banalyze\b", r"\banalyse\b", r"\banalysis\b",
    r"\bwrite\b", r"\bdraft\b", r"\bcompose\b",
    r"\breview\b", r"\bevaluate\b", r"\bassess\b",
    r"\brewrite\b", r"\bparaphrase\b",
    r"\bexpand\b", "\belaborate\b",
    r"\bsuggest\b", r"\brecommend\b",
    r"\boutline\b", r"\bplan\b",
    r"\bcreate\b", r"\bgenerate\b",
    r"\bclassify\b", r"\bcategorize\b",
    r"\binterpret\b", r"\bunderstand\b",
    r"\bpredict\b", r"\bforecast\b",
    r"\bscore\b", r"\brank\b",
    r"\bsummarize and\b", r"\bstep.by.step\b",
]

COMPLEX_PATTERNS = [
    r"\bcode\b", r"\bprogram\b", r"\bimplement\b",
    r"\barchitect\b", r"\barchitecture\b", r"\bdesign system\b",
    r"\bdebug\b", r"\btroubleshoot\b", r"\bfix bug\b",
    r"\bdesign\b", r"\bengineer\b",
    r"\breason\b", r"\breasoning\b", r"\bthink through\b",
    r"\balgorithm\b", r"\boptimize\b",
    r"\brefactor\b", r"\brestructure\b",
    r"\bsecurity\b", r"\bpenetration\b",
    r"\bmulti.step\b", r"\bcomplex logic\b",
    r"\bmathematical\b", r"\bproof\b", r"\btheorem\b",
    r"\bstrategy\b", r"\bstrategic\b",
    r"\btrade.off\b", r"\bpros and cons\b",
    r"\bscale\b", r"\bscalability\b",
    r"\bconcurrent\b", r"\bparallel\b", r"\bdistributed\b",
    r"\bdatabase\b", r"\bsql\b", r"\bquery optimi\b",
    r"\bapi design\b", r"\brest api\b", r"\bgraphql\b",
    r"\bci.cd\b", r"\bdevops\b", r"\bdeploy\b",
    r"\btest\b", r"\bunit test\b", r"\bintegration test\b",
    r"\bregex\b", r"\bregular expression\b",
    r"\bcompiler\b", r"\bparser\b", r"\bast\b",
]

# Task type keywords for categorization
TASK_TYPE_KEYWORDS = {
    "summarization": ["summarize", "summary", "sum up", "tldr", "brief"],
    "translation": ["translate", "translation", "localize"],
    "code_generation": ["code", "implement", "program", "function", "class", "script"],
    "code_review": ["review code", "code review", "check code", "audit"],
    "debugging": ["debug", "fix bug", "troubleshoot", "error", "exception"],
    "writing": ["write", "draft", "compose", "article", "essay", "blog"],
    "analysis": ["analyze", "analysis", "examine", "investigate"],
    "explanation": ["explain", "describe", "clarify", "how does"],
    "math": ["calculate", "compute", "math", "equation", "formula"],
    "data_processing": ["parse", "extract", "transform", "clean", "process data"],
    "planning": ["plan", "outline", "strategy", "roadmap", "design"],
    "creative": ["creative", "story", "poem", "brainstorm", "ideate"],
    "classification": ["classify", "categorize", "label", "tag"],
    "general": [],
}


class TaskClassifier:
    """Classifies task complexity using keyword and pattern matching."""

    def __init__(self) -> None:
        self._simple_patterns = [re.compile(p, re.IGNORECASE) for p in SIMPLE_PATTERNS]
        self._medium_patterns = [re.compile(p, re.IGNORECASE) for p in MEDIUM_PATTERNS]
        self._complex_patterns = [re.compile(p, re.IGNORECASE) for p in COMPLEX_PATTERNS]
        self._task_type_patterns: dict[str, list[re.Pattern]] = {}
        for task_type, keywords in TASK_TYPE_KEYWORDS.items():
            self._task_type_patterns[task_type] = [
                re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in keywords
            ]

    def classify(self, task_description: str) -> TaskComplexity:
        """Classify the complexity of a task.

        Uses a scoring system:
        - Each pattern match adds points to its complexity level
        - Simple patterns score +1 for simple
        - Medium patterns score +1 for medium
        - Complex patterns score +1 for complex
        - Additional heuristics for length and structure
        """
        text = task_description.strip()
        if not text:
            return TaskComplexity.SIMPLE

        scores = {
            TaskComplexity.SIMPLE: 0.0,
            TaskComplexity.MEDIUM: 0.0,
            TaskComplexity.COMPLEX: 0.0,
        }

        # Pattern matching scores
        for pattern in self._simple_patterns:
            if pattern.search(text):
                scores[TaskComplexity.SIMPLE] += 1.0

        for pattern in self._medium_patterns:
            if pattern.search(text):
                scores[TaskComplexity.MEDIUM] += 1.0

        for pattern in self._complex_patterns:
            if pattern.search(text):
                scores[TaskComplexity.COMPLEX] += 1.0

        # Length-based heuristics
        word_count = len(text.split())
        if word_count > 100:
            scores[TaskComplexity.COMPLEX] += 1.5
        elif word_count > 50:
            scores[TaskComplexity.MEDIUM] += 1.0
        elif word_count < 10:
            scores[TaskComplexity.SIMPLE] += 0.5

        # Check for code blocks or technical content
        if re.search(r"```|`[^`]+`", text):
            scores[TaskComplexity.COMPLEX] += 2.0

        # Check for multi-step instructions
        step_indicators = len(re.findall(r"\b(step \d|first|then|finally|next)\b", text, re.IGNORECASE))
        if step_indicators >= 3:
            scores[TaskComplexity.COMPLEX] += 1.5
        elif step_indicators >= 2:
            scores[TaskComplexity.MEDIUM] += 1.0

        # Questions with multiple parts
        question_marks = text.count("?")
        if question_marks >= 3:
            scores[TaskComplexity.COMPLEX] += 1.0
        elif question_marks >= 2:
            scores[TaskComplexity.MEDIUM] += 0.5

        # Return the highest scoring complexity
        max_score = max(scores.values())
        if max_score == 0:
            return TaskComplexity.MEDIUM  # default to medium when no patterns match

        # Tie-breaking: prefer higher complexity
        for level in [TaskComplexity.COMPLEX, TaskComplexity.MEDIUM, TaskComplexity.SIMPLE]:
            if scores[level] == max_score:
                return level

        return TaskComplexity.MEDIUM

    def detect_task_type(self, task_description: str) -> str:
        """Detect the type/category of task."""
        text = task_description.strip().lower()
        best_type = "general"
        best_count = 0

        for task_type, patterns in self._task_type_patterns.items():
            count = sum(1 for p in patterns if p.search(text))
            if count > best_count:
                best_count = count
                best_type = task_type

        return best_type

    def get_confidence(self, task_description: str) -> float:
        """Return confidence score (0-1) for the classification."""
        text = task_description.strip()
        if not text:
            return 0.0

        total_matches = 0
        for pattern in self._simple_patterns + self._medium_patterns + self._complex_patterns:
            if pattern.search(text):
                total_matches += 1

        # More matches = higher confidence, capped at 1.0
        return min(1.0, total_matches * 0.2 + 0.3)
