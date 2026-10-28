"""
scripts/generate_openapi_types.py

Generates clean TypeScript type declarations in frontend/src/types/api.ts
from backend FastAPI application OpenAPI schema.
"""

import json
import sys
from pathlib import Path

# Ensure backend on sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.main import app

TYPE_MAPPING = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "array": "any[]",
    "object": "Record<string, any>",
}


def python_type_to_ts(schema: dict, openapi_schemas: dict) -> str:
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        return ref_name

    if "anyOf" in schema:
        types = [python_type_to_ts(s, openapi_schemas) for s in schema["anyOf"]]
        return " | ".join(types)

    t = schema.get("type")
    if t == "array":
        items = schema.get("items", {})
        item_ts = python_type_to_ts(items, openapi_schemas)
        return f"{item_ts}[]"
    elif t in TYPE_MAPPING:
        if t == "string" and "enum" in schema:
            return " | ".join(f'"{e}"' for e in schema["enum"])
        return TYPE_MAPPING[t]
    elif "enum" in schema:
        return " | ".join(f'"{e}"' for e in schema["enum"])
    return "any"


def generate_ts():
    openapi = app.openapi()
    schemas = openapi.get("components", {}).get("schemas", {})

    lines = [
        "/**",
        " * Auto-generated Recruit Lens API TypeScript Definitions",
        " * Generated from FastAPI OpenAPI schema.",
        " */",
        "",
        'export type CandidateTier = "FastTrack" | "Review" | "Hold" | "Reject" | "Abstain";',
        'export type RecruiterDecision = "pending" | "shortlisted" | "interviewed" | "held" | "rejected" | "hired";',
        'export type EvaluationStage = "screened" | "shortlisted" | "interview_scheduled" | "interviewed" | "offer_extended" | "hired" | "rejected" | "held";',
        "",
    ]

    for name, s in sorted(schemas.items()):
        props = s.get("properties", {})
        required = set(s.get("required", []))
        desc = s.get("description", "")

        if desc:
            lines.append(f"/** {desc} */")
        lines.append(f"export interface {name} {{")
        for p_name, p_schema in props.items():
            is_req = p_name in required
            ts_type = python_type_to_ts(p_schema, schemas)
            prop_desc = p_schema.get("description")
            if prop_desc:
                lines.append(f"  /** {prop_desc} */")
            lines.append(f"  {p_name}{'' if is_req else '?'}: {ts_type};")
        lines.append("}\n")

    out_file = Path(__file__).resolve().parent.parent / "frontend" / "src" / "types" / "api.ts"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated {len(schemas)} schemas into {out_file}")


if __name__ == "__main__":
    generate_ts()
