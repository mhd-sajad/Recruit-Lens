"""
remap_gold_pairs_v2.py

Re-maps the 34 gold evaluation pairs onto the freshly cleaned chunks in data/chunks_batch1_verified/.
Verifies fuzzy containment (substring or fuzzy ratio >= 0.85).
Drops any uncontained pair and records it.
Saves docs/eval_pairs_remapped_v2.json.
Prints 10 random remapped pairs raw.
"""

import difflib
import json
import random
from pathlib import Path

# Ground-truth evidence queries and text phrases for each pair
GOLD_EVIDENCE_SPEC = [
    {
        "pair_idx": 1,
        "resume_id": "62994611",
        "query": "Requires strong proficiency in Python and RESTful API development.",
        "evidence_text": "Experienced in c#, python, HTML, SQL, implementations.",
        "target_chunk": "62994611_001",
    },
    {
        "pair_idx": 2,
        "resume_id": "21297521",
        "query": "Experience with containerization tools like Docker and Kubernetes.",
        "evidence_text": "containers such as Docker and Rkt, Keen interest in Cloud Native Computing Foundation's (CNCF) OCI and eXtreme Programming, Waterfall in a highly regulated environment. DevOps using Agile methodologies, Git based development workflows, Automated unit testing and end-to-end (e2e) testing",
        "target_chunk": "21297521_010",
    },
    {
        "pair_idx": 3,
        "resume_id": "83816738",
        "query": "Familiarity with CI/CD pipelines and tools like Jenkins.",
        "evidence_text": "Build Tools: Gradle, Maven, Ant Practices: Agile/Scrum, Waterfall, TDD, Clean Coding, Continuous Architectures: Microservices, Single Page Application, REST, Version Control: SVN, Git Cloud Application Platform: AWS Others: Bower, Grunt, Npm, Node, JSON, XML, Jenkins",
        "target_chunk": "83816738_002",
    },
    {
        "pair_idx": 4,
        "resume_id": "83816738",
        "query": "Strong frontend development skills using React.js.",
        "evidence_text": "Extensive experience in developing Web interfaces using HTML5, ReactJS and BackboneJS.",
        "target_chunk": "83816738_001",
    },
    {
        "pair_idx": 5,
        "resume_id": "83816738",
        "query": "Understanding of Agile/Scrum methodologies.",
        "evidence_text": "Expertise working in Agile methodology environments like Scrum.",
        "target_chunk": "83816738_001",
    },
    {
        "pair_idx": 6,
        "resume_id": "50328713",
        "query": "Familiarity with machine learning frameworks like TensorFlow or PyTorch.",
        "evidence_text": "Seaborn, matplotlib, TensorFlow (basic). (I built a XGBoost Codes LAMMPS, and LIGGGHTS. and analysis;",
        "target_chunk": "50328713_008",
    },
    {
        "pair_idx": 7,
        "resume_id": "18448085",
        "query": "Data visualization skills using Tableau or PowerBI.",
        "evidence_text": "Excel, MS Visio, Tableau MySQL, Oracle Database, Microsoft Access",
        "target_chunk": "18448085_001",
    },
    {
        "pair_idx": 8,
        "resume_id": "30863060",
        "query": "Proficient in SQL for complex data extraction.",
        "evidence_text": "Database Analyst",
        "target_chunk": "30863060_003",
    },
    {
        "pair_idx": 9,
        "resume_id": "34953092",
        "query": "Deep understanding of deep learning algorithms and neural networks.",
        "evidence_text": "Deep Neural Networks",
        "target_chunk": "34953092_002",
    },
    {
        "pair_idx": 10,
        "resume_id": "24574164",
        "query": "Experience leading product roadmap from conception to launch.",
        "evidence_text": "Director, Ad Products",
        "target_chunk": "24574164_004",
    },
    {
        "pair_idx": 11,
        "resume_id": "12085736",
        "query": "Experience in B2B SaaS product environments.",
        "evidence_text": "SaaS ad serving management software AdJuggler",
        "target_chunk": "12085736_006",
    },
    {
        "pair_idx": 12,
        "resume_id": "20330739",
        "query": "Go-to-market (GTM) strategy execution.",
        "evidence_text": "go-to-market strategies and positioning to achieve optimal goals",
        "target_chunk": "20330739_003",
    },
    {
        "pair_idx": 13,
        "resume_id": "34185495",
        "query": "Financial modeling and valuation experience (DCF, LBO).",
        "evidence_text": "dynamic financial models, including DCF, tax credit analysis, investment return analysis, capitalization rate-based and multiple- based valuations",
        "target_chunk": "34185495_005",
    },
    {
        "pair_idx": 14,
        "resume_id": "14181049",
        "query": "Proficiency in Advanced Excel (VBA, Macros).",
        "evidence_text": "Advanced Excel",
        "target_chunk": "14181049_002",
    },
    {
        "pair_idx": 15,
        "resume_id": "29406313",
        "query": "Experience in portfolio management and risk assessment.",
        "evidence_text": "Portfolio Management Streamline Operations Business Development New Market Expansion New Product Development Process Reengineering Multi-Site Operations Regulatory Compliance Loss Mitigation Strategic / Tactical Planning Project Management Team Recruitment and Leadership Risk Assessment and Analysis",
        "target_chunk": "29406313_001",
    },
    {
        "pair_idx": 16,
        "resume_id": "24530382",
        "query": "Background in corporate FP&A (Financial Planning & Analysis).",
        "evidence_text": "Financial Planning and Analysis Business Process Re-engineering Mergers and Acquisitions Strategic and Operational Achievements",
        "target_chunk": "24530382_001",
    },
    {
        "pair_idx": 17,
        "resume_id": "25749150",
        "query": "Familiarity with HIPAA compliance and patient data privacy.",
        "evidence_text": "Retrieved patient medical records from physicians, technicians, or coverage and billing of all detailed procedures reports, and remittances to insurance companies with regulations. prior to services being rendered. and pre-authorization functions by appropriately handling patient",
        "target_chunk": "25749150_006",
    },
    {
        "pair_idx": 18,
        "resume_id": "17555081",
        "query": "Clinical trial management and FDA submission experience.",
        "evidence_text": "Clinical Research Coordinator",
        "target_chunk": "17555081_004",
    },
    {
        "pair_idx": 19,
        "resume_id": "32081266",
        "query": "Experience with Electronic Health Record (EHR) systems like Epic.",
        "evidence_text": "Electronic Health Records",
        "target_chunk": "32081266_002",
    },
    {
        "pair_idx": 20,
        "resume_id": "24349611",
        "query": "Background in molecular biology or PCR techniques.",
        "evidence_text": "molecular biology",
        "target_chunk": "24349611_002",
    },
    {
        "pair_idx": 21,
        "resume_id": "23918545",
        "query": "Knowledge of medical billing and coding (ICD-10).",
        "evidence_text": "ICD-10",
        "target_chunk": "23918545_002",
    },
    {
        "pair_idx": 22,
        "resume_id": "13837784",
        "query": "Experience managing paid social campaigns (Facebook, LinkedIn).",
        "evidence_text": "paid social",
        "target_chunk": "13837784_004",
    },
    {
        "pair_idx": 23,
        "resume_id": "30504149",
        "query": "SEO/SEM strategy and execution.",
        "evidence_text": "SEO/SEM",
        "target_chunk": "30504149_001",
    },
    {
        "pair_idx": 24,
        "resume_id": "15423153",
        "query": "Proficiency with email marketing platforms like Mailchimp or Hubspot.",
        "evidence_text": "automated email marketing",
        "target_chunk": "15423153_004",
    },
    {
        "pair_idx": 25,
        "resume_id": "14128006",
        "query": "Experience with Google Analytics and conversion tracking.",
        "evidence_text": "Google Analytics",
        "target_chunk": "14128006_003",
    },
    {
        "pair_idx": 26,
        "resume_id": "11890896",
        "query": "Supply chain optimization and inventory management.",
        "evidence_text": "inventory control",
        "target_chunk": "11890896_003",
    },
    {
        "pair_idx": 27,
        "resume_id": "12904972",
        "query": "Lean Six Sigma or continuous improvement methodologies.",
        "evidence_text": "Six Sigma and Lean",
        "target_chunk": "12904972_003",
    },
    {
        "pair_idx": 28,
        "resume_id": "26341987",
        "query": "Vendor negotiation and procurement experience.",
        "evidence_text": "Key Contracts negotiations, Procurement, Software licensing",
        "target_chunk": "26341987_005",
    },
    {
        "pair_idx": 29,
        "resume_id": "20176584",
        "query": "Experience managing warehouse staff and safety protocols.",
        "evidence_text": "managing the maintenance team and associated budgets and $200 billion of USAF hardware while safely transferring over 1 million gallons",
        "target_chunk": "20176584_001",
    },
    {
        "pair_idx": 30,
        "resume_id": "65708020",
        "query": "Proven track record of exceeding B2B sales quotas.",
        "evidence_text": "exceed sales quotas",
        "target_chunk": "65708020_003",
    },
    {
        "pair_idx": 31,
        "resume_id": "29825044",
        "query": "Experience using Salesforce CRM to manage pipelines.",
        "evidence_text": "Proficiency in administration of Salesforce and Microsoft reports and dashboards",
        "target_chunk": "29825044_002",
    },
    {
        "pair_idx": 32,
        "resume_id": "91467795",
        "query": "Cold calling and outbound prospecting skills.",
        "evidence_text": "new business opportunities through cold calling",
        "target_chunk": "91467795_007",
    },
    {
        "pair_idx": 33,
        "resume_id": "21283365",
        "query": "Proven ability to sell SaaS products to Enterprise clients.",
        "evidence_text": "I was hired in 05' to put in place all things SaaS, this included designing",
        "target_chunk": "21283365_005",
    },
    {
        "pair_idx": 34,
        "resume_id": "35673335",
        "query": "Contract negotiation and closing complex enterprise deals.",
        "evidence_text": "negotiations for $3M/year Verizon Wireless contract, in a six-month",
        "target_chunk": "35673335_004",
    },
]


def compute_fuzzy_containment(evidence: str, chunk_text: str) -> float:
    ev = evidence.lower().strip()
    ct = chunk_text.lower().strip()
    if not ev or not ct:
        return 0.0
    if ev in ct:
        return 1.0

    # Sliding word window matching
    words_ev = ev.split()
    words_ct = ct.split()
    if not words_ev:
        return 0.0
    L = len(words_ev)
    best_ratio = 0.0
    for s in range(0, max(1, len(words_ct) - L + 1)):
        span = " ".join(words_ct[s : s + L])
        r = difflib.SequenceMatcher(None, ev, span).ratio()
        if r > best_ratio:
            best_ratio = r
    return round(best_ratio, 4)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    chunks_dir = repo_root / "data" / "chunks_batch1_verified"

    with open(repo_root / "docs" / "eval_pairs_locked.json", encoding="utf-8") as f:
        locked_pairs = json.load(f)

    remapped_pairs = []
    dropped_pairs = []

    for spec, locked in zip(GOLD_EVIDENCE_SPEC, locked_pairs):
        rid = spec["resume_id"]
        q = spec["query"]
        ev = spec["evidence_text"]
        target_chunk_id = spec["target_chunk"]
        domain = locked.get("domain", "")
        old_chunk_id = locked.get("relevant_chunk_id", "")

        chunk_file = chunks_dir / f"{rid}.json"
        if not chunk_file.exists():
            dropped_pairs.append({"query": q, "reason": "chunk file missing"})
            continue

        with open(chunk_file, encoding="utf-8") as f:
            chunks = json.load(f)

        chunk_dict = {c["chunk_id"]: c for c in chunks}

        # Check if target_chunk exists and contains evidence
        chosen_chunk = chunk_dict.get(target_chunk_id)
        ratio = 0.0
        if chosen_chunk:
            ratio = compute_fuzzy_containment(ev, chosen_chunk["text"])

        # Fallback search if ratio < 0.85
        if ratio < 0.85:
            for c in chunks:
                r = compute_fuzzy_containment(ev, c["text"])
                if r > ratio:
                    ratio = r
                    chosen_chunk = c

        if chosen_chunk and ratio >= 0.85:
            remapped_pairs.append(
                {
                    "domain": domain,
                    "query": q,
                    "resume_id": rid,
                    "old_chunk_id": old_chunk_id,
                    "relevant_chunk_id": chosen_chunk["chunk_id"],
                    "relevance_score": 2,
                    "gold_evidence_text": ev,
                    "remapped_chunk_text": chosen_chunk["text"],
                    "fuzzy_containment_ratio": ratio,
                }
            )
        else:
            dropped_pairs.append(
                {
                    "query": q,
                    "old_chunk_id": old_chunk_id,
                    "best_ratio": ratio,
                    "evidence_text": ev,
                }
            )

    out_file = repo_root / "docs" / "eval_pairs_remapped_v2.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(remapped_pairs, f, indent=2)

    print(f"\n--- GOLD PAIR REMAPPING COMPLETE ---")
    print(f"Total locked pairs: {len(locked_pairs)}")
    print(f"Successfully remapped (ratio >= 0.85): {len(remapped_pairs)}")
    print(f"Dropped pairs: {len(dropped_pairs)}")
    print(f"Saved to {out_file}\n")

    # Print 10 random remapped pairs raw as requested
    random.seed(42)
    sample_10 = random.sample(remapped_pairs, min(10, len(remapped_pairs)))

    print("=" * 80)
    print("10 RANDOM REMAPPED GOLD PAIRS (RAW OUTPUT)")
    print("=" * 80)
    for idx, p in enumerate(sample_10, 1):
        print(f"\n[PAIR #{idx}]")
        print(f"Resume ID:               {p['resume_id']}")
        print(f"Query:                   {p['query']}")
        print(f"Gold Evidence Text:      {p['gold_evidence_text']}")
        print(f"Remapped Chunk ID:       {p['relevant_chunk_id']}")
        print(f"Fuzzy Containment Ratio: {p['fuzzy_containment_ratio']}")
        print(f"Remapped Chunk Preview:  {p['remapped_chunk_text'][:160]}...")
    print("=" * 80)


if __name__ == "__main__":
    main()
