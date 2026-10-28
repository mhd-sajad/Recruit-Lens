"""
Skill Taxonomy Module

Loads the curated O*NET-backed technology taxonomy (8,700+ skills across 130+ families),
handles canonicalization of aliases, pattern-based phrase matching with boundary guards,
and relation-based skill inference (e.g. Django implies Python).
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills_taxonomy.json"


class SkillTaxonomy:
    """Production skill taxonomy supporting canonical alias resolution and inference."""

    _instance: "SkillTaxonomy | None" = None

    def __init__(self, taxonomy_path: Path | str | None = None) -> None:
        if taxonomy_path is None:
            taxonomy_path = DEFAULT_TAXONOMY_PATH
        self.taxonomy_path = Path(taxonomy_path)

        self._canonical_skills: dict[str, dict[str, Any]] = {}
        self._alias_map: dict[str, str] = {}
        self._inference_map: dict[str, list[dict[str, Any]]] = {}
        self._patterns: list[tuple[re.Pattern[str], str]] = []

        self._load_taxonomy()
        self._compile_matchers()

    @classmethod
    def get_instance(cls, taxonomy_path: Path | str | None = None) -> "SkillTaxonomy":
        """Singleton accessor for in-memory taxonomy."""
        if cls._instance is None:
            cls._instance = SkillTaxonomy(taxonomy_path)
        return cls._instance

    def _load_taxonomy(self) -> None:
        if self.taxonomy_path.exists():
            try:
                with open(self.taxonomy_path, encoding="utf-8") as f:
                    data = json.load(f)
                for item in data.get("skills", []):
                    canon = item["canonical_name"]
                    self._canonical_skills[canon.lower()] = item
                self._alias_map = data.get("alias_to_canonical", {})
                self._inference_map = data.get("inference_relations", {})
                logger.info(
                    "Loaded %d skills from %s", len(self._canonical_skills), self.taxonomy_path
                )
                return
            except Exception as e:
                logger.warning("Failed to load taxonomy from %s: %e", self.taxonomy_path, e)

        # Minimal fallback
        self._canonical_skills = {
            "python": {"canonical_name": "Python", "family": "Programming Languages"},
            "javascript": {"canonical_name": "JavaScript", "family": "Programming Languages"},
            "kubernetes": {"canonical_name": "Kubernetes", "family": "DevOps & Cloud"},
            "docker": {"canonical_name": "Docker", "family": "DevOps & Cloud"},
        }
        self._alias_map = {
            "py": "Python",
            "python": "Python",
            "js": "JavaScript",
            "javascript": "JavaScript",
            "k8s": "Kubernetes",
            "kubernetes": "Kubernetes",
            "docker": "Docker",
        }

    def _compile_matchers(self) -> None:
        """
        Pre-compile regex matchers sorted by length descending so multi-word phrases
        (e.g., 'machine learning') match before single words (e.g., 'learning').
        """
        sorted_aliases = sorted(self._alias_map.keys(), key=len, reverse=True)
        short_keep = {"c#", "c++", "r", "go", "js", "ts", "py", "ui", "ux", "ai", "ml", "dl", "db"}
        filtered_aliases = [a for a in sorted_aliases if len(a) > 2 or a in short_keep]

        self._patterns = []
        for alias in filtered_aliases:
            canon = self._alias_map[alias]
            # Use strict word boundaries
            escaped = re.escape(alias)
            if alias in {"c++", "c#"}:
                pattern = re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)
            else:
                pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
            self._patterns.append((pattern, canon))

    @property
    def total_skills(self) -> int:
        return len(self._canonical_skills)

    def canonicalize(self, raw_name: str) -> str | None:
        """Resolve a raw skill string to canonical form."""
        cleaned = raw_name.strip().lower()
        return self._alias_map.get(cleaned)

    def get_family(self, canonical_name: str) -> str:
        """Return the category family of a skill."""
        item = self._canonical_skills.get(canonical_name.lower())
        if item:
            return str(item.get("family", "General Technology"))
        return "General Technology"

    def get_inferred_skills(self, canonical_name: str) -> list[tuple[str, float]]:
        """Return list of (inferred_skill_name, confidence) based on taxonomy relations."""
        norm = canonical_name.lower()
        relations = self._inference_map.get(norm, [])
        return [(r["skill"], float(r["confidence"])) for r in relations]

    def extract_skills_from_text(self, text: str) -> list[dict[str, Any]]:
        """
        Extract all taxonomy-recognized skills from free text with match spans and canonical names.
        """
        if not text.strip():
            return []

        matched_skills: dict[str, dict[str, Any]] = {}

        for pattern, canon in self._patterns:
            for match in pattern.finditer(text):
                norm_canon = canon.lower()
                span = match.span()
                matched_text = match.group()

                if norm_canon not in matched_skills:
                    matched_skills[norm_canon] = {
                        "skill": canon,
                        "family": self.get_family(canon),
                        "first_matched_text": matched_text,
                        "occurrences": 1,
                        "spans": [span],
                    }
                else:
                    matched_skills[norm_canon]["occurrences"] += 1
                    matched_skills[norm_canon]["spans"].append(span)

        return list(matched_skills.values())
