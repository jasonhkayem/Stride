from __future__ import annotations

from pathlib import Path
from typing import Dict, List

# Load .env before importing anything that reads DATABASE_URL
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from training.db import SessionLocal
from training.training_plan_templates.models import TrainingPlanTemplate


TEMPLATES: List[Dict] = [
    {
        "goal_race": "5k",
        "duration_weeks": 8,
        "structure": {
            "min_runs_per_week": 2,
            "description": "Beginner 5K base plan",
        },
    },
    {
        "goal_race": "10k",
        "duration_weeks": 10,
        "structure": {
            "min_runs_per_week": 2,
            "description": "Beginner 10K base plan",
        },
    },
    {
        "goal_race": "half_marathon",
        "duration_weeks": 12,
        "structure": {
            "min_runs_per_week": 3,
            "description": "Half marathon base plan",
        },
    },
    {
        "goal_race": "marathon",
        "duration_weeks": 16,
        "structure": {
            "min_runs_per_week": 4,
            "description": "Marathon base plan",
        },
    },
]


def main() -> int:
    created = 0
    skipped = 0
    with SessionLocal() as session:
        for tpl in TEMPLATES:
            exists = (
                session.query(TrainingPlanTemplate)
                .filter(TrainingPlanTemplate.goal_race == tpl["goal_race"])
                .first()
            )
            if exists:
                skipped += 1
                continue
            session.add(TrainingPlanTemplate(**tpl))
            created += 1
        session.commit()
    print(f"seeded templates: created={created}, skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
