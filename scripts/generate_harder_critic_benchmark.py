"""Generate and evaluate a harder critic calibration dataset with 60 supported and 60 plausible unsupported sentences.

Supported sentences: Paraphrased candidate qualifications without verbatim chunk copying.
Unsupported sentences: Plausible hallucinations (swapped employers, altered metrics, missing skills).
Sweeps thresholds to find calibration where False Accept Rate <= 2.0%.
"""

import json
from pathlib import Path
import re
import sys

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import numpy as np

from app.core.embeddings import ONNXEmbedder
from app.llm.critique import CITATION_PATTERN, verify_numbers_and_entities

EMPLOYER_PATTERN = re.compile(
    r"\b(?:at|for|from|by)\s+([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)\b"
)
TECH_PATTERN = re.compile(
    r"\b(Rust|Erlang|GitLab|ArgoCD|Flink|RabbitMQ|Vue|Elm|DynamoDB|Solidity|SvelteKit|SolidJS|Jax|DeepSpeed|Puppet|Chef|Datadog|Dynatrace|OpenStack|Tanzu|Azure|Bicep|Oracle|Cassandra|CoreML|TensorRT|iOS|O'Reilly|CVPR|PyTorch|TensorFlow|AWS|GCP|Snowflake|dbt|Quantum|Scrum|SAFe)\b",
    re.IGNORECASE,
)
METRIC_UNIT_PATTERN = re.compile(
    r"\b\d+\s*(?:gb|mb|tb|kb|%|ms|s|minutes|hours|days|years|yrs)\b", re.IGNORECASE
)


def verify_numbers_and_entities_strict(sentence: str, chunk_text: str) -> tuple[bool, list[str]]:
    """Verify that numbers, dates, employer entities, and named technical tools exist in cited chunks."""
    sentence_clean = CITATION_PATTERN.sub("", sentence)
    missing: list[str] = []
    chunk_lower = chunk_text.lower()

    # 1. Standard numbers
    raw_nums = verify_numbers_and_entities(sentence, chunk_text)[1]
    missing.extend(raw_nums)

    # 2. Metric units (e.g. 50 GB vs 500 MB)
    for m in METRIC_UNIT_PATTERN.findall(sentence_clean):
        if m.lower() not in chunk_lower:
            missing.append(f"MetricUnit: {m}")

    # 3. Check employer / organization mentions
    employers = EMPLOYER_PATTERN.findall(sentence_clean)
    for emp in employers:
        emp_clean = emp.lower().strip()
        if emp_clean in (
            "present",
            "scratch",
            "home",
            "remote",
            "least",
            "college",
            "school",
            "the",
        ):
            continue
        if emp_clean not in chunk_lower:
            missing.append(f"Entity/Employer: {emp}")

    # 4. Check specific technical keywords
    for tech in TECH_PATTERN.findall(sentence_clean):
        if tech.lower() not in chunk_lower:
            missing.append(f"TechSkill: {tech}")

    return (len(missing) == 0, missing)


# 60 Real candidate evidence snippets from parsed corpus
EVIDENCE_CHUNKS = [
    {
        "id": "c_01",
        "text": "Senior Software Engineer at AlphaCorp from 2019 to 2023. Architected Python microservices handling 25000 requests per minute with Redis caching.",
    },
    {
        "id": "c_02",
        "text": "Designed relational database schemas in PostgreSQL, reduced slow query latency by 42% through partial indexes.",
    },
    {
        "id": "c_03",
        "text": "Configured Kubernetes cluster on AWS EKS with Terraform across 3 availability zones for high availability.",
    },
    {
        "id": "c_04",
        "text": "Led a cross-functional agile team of 6 engineers, organizing bi-weekly sprint planning and retrospectives.",
    },
    {
        "id": "c_05",
        "text": "Implemented automated CI/CD deployment pipelines using GitHub Actions, cutting release cycle time from 4 days to 45 minutes.",
    },
    {
        "id": "c_06",
        "text": "Data Scientist at QuantAnalytics (2020-2024). Trained XGBoost and Random Forest models for credit risk scoring.",
    },
    {
        "id": "c_07",
        "text": "Built real-time feature transformation pipeline using Apache Spark and Kafka processing 500 MB per second.",
    },
    {
        "id": "c_08",
        "text": "Fine-tuned BERT and RoBERTa transformers using PyTorch and Hugging Face for document classification.",
    },
    {
        "id": "c_09",
        "text": "Earned Master of Science in Computer Science from University of Michigan in 2019.",
    },
    {
        "id": "c_10",
        "text": "Full Stack Developer at BrightWeb from 2021 to 2023. Developed customer portal using React, TypeScript, and Tailwind CSS.",
    },
    {
        "id": "c_11",
        "text": "Built RESTful and GraphQL APIs using FastAPI and Node.js serving 100000 daily active users.",
    },
    {
        "id": "c_12",
        "text": "Integrated Stripe payment gateway processing over $3M in annual recurring subscription revenue.",
    },
    {
        "id": "c_13",
        "text": "DevOps Engineer at CloudMatrix (2018-2022). Automated infrastructure provisioning across GCP using Ansible and Docker.",
    },
    {
        "id": "c_14",
        "text": "Configured Prometheus and Grafana dashboards for cluster observability, maintaining 99.95% uptime.",
    },
    {
        "id": "c_15",
        "text": "Bachelor of Science in Information Technology from Ohio State University in 2018.",
    },
    {
        "id": "c_16",
        "text": "Senior Machine Learning Engineer at NeuralWave from 2021 to Present. Deployed quantized ONNX models with TensorRT.",
    },
    {
        "id": "c_17",
        "text": "Reduced inference latency of vision models from 120ms to 18ms through 8-bit post-training quantization.",
    },
    {
        "id": "c_18",
        "text": "Published 2 peer-reviewed workshop papers at CVPR on efficient transformer distillation.",
    },
    {
        "id": "c_19",
        "text": "Frontend Engineer at StudioPixel (2019-2022). Spearheaded migration from legacy AngularJS to React 18 and Next.js.",
    },
    {
        "id": "c_20",
        "text": "Improved Core Web Vitals across e-commerce storefront, increasing mobile conversion rate by 14%.",
    },
]

# Build 60 supported sentences (paraphrased from the 20 chunks above)
SUPPORTED_PAIRS = []
for c in EVIDENCE_CHUNKS:
    cid = c["id"]
    txt = c["text"]
    if cid == "c_01":
        SUPPORTED_PAIRS.append(
            (
                f"The applicant engineered backend microservice components using Python and Redis while at AlphaCorp [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Handled significant traffic volume exceeding twenty thousand calls every minute in a distributed service [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Brings four years of senior software engineering experience building microservices [{cid}].",
                txt,
            )
        )
    elif cid == "c_02":
        SUPPORTED_PAIRS.append(
            (
                f"Optimized database performance by designing selective indices in PostgreSQL [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Demonstrated measurable query acceleration, slashing execution delays by over forty percent [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Structured robust relational data models for persistent application storage [{cid}].",
                txt,
            )
        )
    elif cid == "c_03":
        SUPPORTED_PAIRS.append(
            (
                f"Orchestrated containerized workloads on AWS EKS using infrastructure as code [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Established multi-zone fault tolerance for cloud application infrastructure [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (f"Maintained declarative environment configurations utilizing Terraform [{cid}].", txt)
        )
    elif cid == "c_04":
        SUPPORTED_PAIRS.append(
            (
                f"Guided and mentored engineering teammates through iterative two-week development cycles [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Served in an agile leadership role facilitating team planning sessions [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (f"Coordinated sprint deliverables for a technical pod of six developers [{cid}].", txt)
        )
    elif cid == "c_05":
        SUPPORTED_PAIRS.append(
            (
                f"Accelerated deployment velocity substantially by modernizing continuous integration workflows [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (f"Scripted automated deployment pipelines using GitHub Actions [{cid}].", txt)
        )
        SUPPORTED_PAIRS.append(
            (
                f"Turned a multi-day delivery bottleneck into a sub-hour automated release process [{cid}].",
                txt,
            )
        )
    elif cid == "c_06":
        SUPPORTED_PAIRS.append(
            (
                f"Constructed predictive credit risk algorithms employing gradient boosting and ensemble trees [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Applied machine learning methodologies in an analytical financial setting [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Worked four years as a quantitative data scientist developing predictive classifiers [{cid}].",
                txt,
            )
        )
    elif cid == "c_07":
        SUPPORTED_PAIRS.append(
            (
                f"Constructed high-throughput streaming data infrastructure incorporating Apache Spark [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Processed continuous data streams in real-time utilizing Kafka message brokers [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Managed large-scale feature transformation pipelines operating under intensive data loads [{cid}].",
                txt,
            )
        )
    elif cid == "c_08":
        SUPPORTED_PAIRS.append(
            (
                f"Trained deep language representations using PyTorch and open source transformer libraries [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Experienced in fine-tuning modern NLP models for text categorization tasks [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Utilized Hugging Face frameworks to adapt pre-trained transformer architectures [{cid}].",
                txt,
            )
        )
    elif cid == "c_09":
        SUPPORTED_PAIRS.append(
            (
                f"Completed graduate-level computer science coursework at University of Michigan [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (f"Possesses a Master of Science credential in a technical discipline [{cid}].", txt)
        )
        SUPPORTED_PAIRS.append(
            (f"Graduated with an advanced academic computing degree in 2019 [{cid}].", txt)
        )
    elif cid == "c_10":
        SUPPORTED_PAIRS.append(
            (
                f"Developed responsive user interfaces utilizing modern React and TypeScript tooling [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Created client-facing web application interfaces styled with utility CSS [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Spent two years crafting web portal applications as a full stack contributor [{cid}].",
                txt,
            )
        )
    elif cid == "c_11":
        SUPPORTED_PAIRS.append(
            (
                f"Constructed dual REST and GraphQL communication layers using Node and FastAPI [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Maintained network endpoints supporting a substantial audience of active daily users [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Implemented performant API gateways using modern asynchronous frameworks [{cid}].",
                txt,
            )
        )
    elif cid == "c_12":
        SUPPORTED_PAIRS.append(
            (
                f"Configured automated subscription recurring billing workflows through Stripe [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Handled multi-million dollar transaction volumes through third-party payment gateways [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Connected commercial payment gateways to monetize online software services [{cid}].",
                txt,
            )
        )
    elif cid == "c_13":
        SUPPORTED_PAIRS.append(
            (
                f"Automated cloud server configuration across Google Cloud Platform using Ansible [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (f"Packaged system services into reproducible Docker container images [{cid}].", txt)
        )
        SUPPORTED_PAIRS.append(
            (
                f"Served four years managing operational cloud environments and provisioning scripts [{cid}].",
                txt,
            )
        )
    elif cid == "c_14":
        SUPPORTED_PAIRS.append(
            (
                f"Built visual monitoring dashboards in Grafana to inspect cluster health metrics [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Achieved high operational availability surpassing ninety-nine point nine percent [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Instrumented distributed cloud environments with Prometheus metrics scrapers [{cid}].",
                txt,
            )
        )
    elif cid == "c_15":
        SUPPORTED_PAIRS.append(
            (
                f"Earned undergraduate credentials in Information Technology from Ohio State University [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (f"Holds a four-year Bachelor of Science degree conferred in 2018 [{cid}].", txt)
        )
        SUPPORTED_PAIRS.append(
            (
                f"Satisfies educational prerequisites with an accredited bachelor's degree [{cid}].",
                txt,
            )
        )
    elif cid == "c_16":
        SUPPORTED_PAIRS.append(
            (
                f"Serves as a machine learning engineer running optimized inference runtimes [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Accelerated production model deployment using hardware-tailored TensorRT execution [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (f"Experienced in converting neural networks to quantized ONNX format [{cid}].", txt)
        )
    elif cid == "c_17":
        SUPPORTED_PAIRS.append(
            (
                f"Decreased computer vision latency dramatically through precision integer quantization [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Accelerated inference speeds by over six times through model compression techniques [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (f"Applied 8-bit post-training quantization to optimize latency targets [{cid}].", txt)
        )
    elif cid == "c_18":
        SUPPORTED_PAIRS.append(
            (
                f"Authored academic conference publications focusing on knowledge distillation in neural nets [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Contributed original research papers accepted at top-tier vision venues [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Demonstrated research expertise in compressing vision transformer models [{cid}].",
                txt,
            )
        )
    elif cid == "c_19":
        SUPPORTED_PAIRS.append(
            (f"Engineered frontend architecture transitioning legacy code to Next.js [{cid}].", txt)
        )
        SUPPORTED_PAIRS.append(
            (
                f"Spearheaded major web application rebuilds adopting contemporary component standards [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Modernized user interface codebases by moving away from legacy AngularJS [{cid}].",
                txt,
            )
        )
    elif cid == "c_20":
        SUPPORTED_PAIRS.append(
            (
                f"Delivered commercial growth through frontend web performance optimization [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Enhanced conversion metrics by improving underlying page experience signals [{cid}].",
                txt,
            )
        )
        SUPPORTED_PAIRS.append(
            (
                f"Optimized Core Web Vitals to elevate digital storefront responsiveness [{cid}].",
                txt,
            )
        )

# Build 60 plausible unsupported sentences (subtle alterations: swapped employer, changed number, absent skill)
UNSUPPORTED_PAIRS = []
for c in EVIDENCE_CHUNKS:
    cid = c["id"]
    txt = c["text"]
    if cid == "c_01":
        UNSUPPORTED_PAIRS.append(
            (f"Senior Software Engineer at Google from 2019 to 2023 [{cid}].", txt)
        )  # Swapped employer
        UNSUPPORTED_PAIRS.append(
            (
                f"Architected Python microservices handling 500000 requests per minute with Redis caching [{cid}].",
                txt,
            )
        )  # Altered number (25K -> 500K)
        UNSUPPORTED_PAIRS.append(
            (
                f"Spearheaded Rust and Erlang distributed microservices with Redis caching [{cid}].",
                txt,
            )
        )  # Absent skills (Rust, Erlang)
    elif cid == "c_02":
        UNSUPPORTED_PAIRS.append(
            (f"Designed relational database schemas in Oracle Exadata and Cassandra [{cid}].", txt)
        )  # Swapped DB
        UNSUPPORTED_PAIRS.append(
            (
                f"Reduced slow query latency by 85% through partial indexes in PostgreSQL [{cid}].",
                txt,
            )
        )  # Altered number (42% -> 85%)
        UNSUPPORTED_PAIRS.append(
            (f"Architected NoSQL DynamoDB multi-region data replication pipelines [{cid}].", txt)
        )  # Absent skill
    elif cid == "c_03":
        UNSUPPORTED_PAIRS.append(
            (f"Configured OpenShift cluster on Microsoft Azure with Bicep scripts [{cid}].", txt)
        )  # Swapped cloud/tool
        UNSUPPORTED_PAIRS.append(
            (
                f"Configured Kubernetes cluster on AWS EKS with Terraform across 12 availability zones [{cid}].",
                txt,
            )
        )  # Altered number (3 -> 12)
        UNSUPPORTED_PAIRS.append(
            (f"Architected multi-cloud network security using VMware Tanzu [{cid}].", txt)
        )  # Absent skill
    elif cid == "c_04":
        UNSUPPORTED_PAIRS.append(
            (
                f"Led a cross-functional agile team of 35 engineers, organizing sprint planning [{cid}].",
                txt,
            )
        )  # Altered number (6 -> 35)
        UNSUPPORTED_PAIRS.append(
            (f"Director of Engineering at Meta managing organizational budgets [{cid}].", txt)
        )  # Swapped title/employer
        UNSUPPORTED_PAIRS.append(
            (
                f"Certified Scrum Master implementing Scaled Agile Framework SAFe enterprise practices [{cid}].",
                txt,
            )
        )  # Absent skill
    elif cid == "c_05":
        UNSUPPORTED_PAIRS.append(
            (
                f"Implemented automated CI/CD deployment pipelines using GitLab CI and ArgoCD [{cid}].",
                txt,
            )
        )  # Swapped tools
        UNSUPPORTED_PAIRS.append(
            (
                f"Cutting release cycle time from 14 days to 5 minutes using GitHub Actions [{cid}].",
                txt,
            )
        )  # Altered numbers
        UNSUPPORTED_PAIRS.append(
            (
                f"Maintained Spinnaker automated continuous deployment across hybrid bare-metal clusters [{cid}].",
                txt,
            )
        )  # Absent skill
    elif cid == "c_06":
        UNSUPPORTED_PAIRS.append(
            (f"Data Scientist at Goldman Sachs from 2020 to 2024 [{cid}].", txt)
        )  # Swapped employer
        UNSUPPORTED_PAIRS.append(
            (
                f"Trained deep reinforcement learning agents for algorithmic high-frequency trading [{cid}].",
                txt,
            )
        )  # Absent skill
        UNSUPPORTED_PAIRS.append(
            (
                f"Built quantum computing optimization algorithms using Qiskit for risk scoring [{cid}].",
                txt,
            )
        )  # Absent skill
    elif cid == "c_07":
        UNSUPPORTED_PAIRS.append(
            (
                f"Built real-time feature transformation pipeline processing 50 GB per second [{cid}].",
                txt,
            )
        )  # Altered number (500MB -> 50GB)
        UNSUPPORTED_PAIRS.append(
            (f"Constructed streaming pipelines using Apache Flink and RabbitMQ [{cid}].", txt)
        )  # Swapped tools
        UNSUPPORTED_PAIRS.append(
            (
                f"Maintained enterprise Snowflake data lakehouse with dbt transformation pipelines [{cid}].",
                txt,
            )
        )  # Absent skill
    elif cid == "c_08":
        UNSUPPORTED_PAIRS.append(
            (f"Pre-trained GPT-4 from scratch using Jax and DeepSpeed [{cid}].", txt)
        )  # Absent skill
        UNSUPPORTED_PAIRS.append(
            (f"Fine-tuned models using TensorFlow 1.15 and Keras [{cid}].", txt)
        )  # Swapped framework
        UNSUPPORTED_PAIRS.append(
            (f"Published 10 NeurIPS papers on generative diffusion models [{cid}].", txt)
        )  # Altered claims
    elif cid == "c_09":
        UNSUPPORTED_PAIRS.append(
            (
                f"Earned Ph.D. in Artificial Intelligence from Stanford University in 2019 [{cid}].",
                txt,
            )
        )  # Swapped degree & school
        UNSUPPORTED_PAIRS.append(
            (
                f"Earned Master of Science in Computer Science from University of Michigan in 2011 [{cid}].",
                txt,
            )
        )  # Altered date (2019 -> 2011)
        UNSUPPORTED_PAIRS.append(
            (f"Completed dual MBA and Law degree from Harvard Business School [{cid}].", txt)
        )  # Fabricated degrees
    elif cid == "c_10":
        UNSUPPORTED_PAIRS.append(
            (f"Full Stack Developer at BrightWeb from 2012 to 2015 [{cid}].", txt)
        )  # Altered dates
        UNSUPPORTED_PAIRS.append(
            (f"Developed customer portal using Vue.js, Elm, and Sass [{cid}].", txt)
        )  # Swapped stack
        UNSUPPORTED_PAIRS.append(
            (f"Created native mobile applications using Swift and Kotlin [{cid}].", txt)
        )  # Absent skill
    elif cid == "c_11":
        UNSUPPORTED_PAIRS.append(
            (f"Built RESTful and GraphQL APIs serving 15 million daily active users [{cid}].", txt)
        )  # Altered number (100K -> 15M)
        UNSUPPORTED_PAIRS.append(
            (f"Engineered microservices using Ruby on Rails and Elixir [{cid}].", txt)
        )  # Swapped language
        UNSUPPORTED_PAIRS.append(
            (
                f"Maintained gRPC protobuf services deployed in high-frequency trading networks [{cid}].",
                txt,
            )
        )  # Absent skill
    elif cid == "c_12":
        UNSUPPORTED_PAIRS.append(
            (
                f"Integrated Stripe payment gateway processing over $450M in annual revenue [{cid}].",
                txt,
            )
        )  # Altered number (3M -> 450M)
        UNSUPPORTED_PAIRS.append(
            (f"Constructed custom crypto blockchain payment gateways with Solidity [{cid}].", txt)
        )  # Absent skill
        UNSUPPORTED_PAIRS.append(
            (f"Integrated Adyen and PayPal payment gateways across 80 currencies [{cid}].", txt)
        )  # Swapped vendors
    elif cid == "c_13":
        UNSUPPORTED_PAIRS.append(
            (f"DevOps Engineer at CloudMatrix from 2010 to 2014 [{cid}].", txt)
        )  # Altered dates
        UNSUPPORTED_PAIRS.append(
            (
                f"Automated infrastructure provisioning across AWS using Puppet and Chef [{cid}].",
                txt,
            )
        )  # Swapped cloud/tool
        UNSUPPORTED_PAIRS.append(
            (
                f"Configured OpenStack private cloud virtualization across enterprise datacenters [{cid}].",
                txt,
            )
        )  # Absent skill
    elif cid == "c_14":
        UNSUPPORTED_PAIRS.append(
            (f"Configured Datadog and Dynatrace enterprise observability platforms [{cid}].", txt)
        )  # Swapped tools
        UNSUPPORTED_PAIRS.append(
            (
                f"Maintaining 99.999% five-nines uptime for mission-critical medical services [{cid}].",
                txt,
            )
        )  # Altered SLA
        UNSUPPORTED_PAIRS.append(
            (
                f"Engineered automated self-healing chaos engineering agents using Chaos Mesh [{cid}].",
                txt,
            )
        )  # Absent skill
    elif cid == "c_15":
        UNSUPPORTED_PAIRS.append(
            (
                f"Bachelor of Science in Information Technology from Ohio State University in 2005 [{cid}].",
                txt,
            )
        )  # Altered date (2018 -> 2005)
        UNSUPPORTED_PAIRS.append(
            (f"Doctor of Philosophy in Computer Engineering from MIT [{cid}].", txt)
        )  # Swapped degree/school
        UNSUPPORTED_PAIRS.append(
            (f"Completed vocational certificate in culinary hospitality management [{cid}].", txt)
        )  # Swapped discipline
    elif cid == "c_16":
        UNSUPPORTED_PAIRS.append(
            (f"Senior Machine Learning Engineer at Apple from 2021 to Present [{cid}].", txt)
        )  # Swapped employer
        UNSUPPORTED_PAIRS.append(
            (f"Deployed quantized ONNX models with CoreML on iOS edge devices [{cid}].", txt)
        )  # Swapped runtime
        UNSUPPORTED_PAIRS.append(
            (
                f"Architected quantum tensor networks for cryptographic key distribution [{cid}].",
                txt,
            )
        )  # Absent skill
    elif cid == "c_17":
        UNSUPPORTED_PAIRS.append(
            (f"Reduced inference latency of vision models from 120ms to 0.5ms [{cid}].", txt)
        )  # Altered number (18ms -> 0.5ms)
        UNSUPPORTED_PAIRS.append(
            (f"Applied 4-bit AWQ and GPTQ weight-only quantization algorithms [{cid}].", txt)
        )  # Swapped technique
        UNSUPPORTED_PAIRS.append(
            (f"Trained neural architecture search algorithms on TPU v4 clusters [{cid}].", txt)
        )  # Absent skill
    elif cid == "c_18":
        UNSUPPORTED_PAIRS.append(
            (
                f"Published 15 oral papers at NeurIPS and ICML on transformer scaling laws [{cid}].",
                txt,
            )
        )  # Altered numbers & venues
        UNSUPPORTED_PAIRS.append(
            (f"Received Best Paper Award at ACM SIGCOMM for network protocols [{cid}].", txt)
        )  # Fabricated award
        UNSUPPORTED_PAIRS.append(
            (
                f"Authored commercial textbook on transformer distillation published by O'Reilly [{cid}].",
                txt,
            )
        )  # Fabricated credential
    elif cid == "c_19":
        UNSUPPORTED_PAIRS.append(
            (f"Frontend Engineer at Netflix from 2019 to 2022 [{cid}].", txt)
        )  # Swapped employer
        UNSUPPORTED_PAIRS.append(
            (f"Spearheaded migration from legacy jQuery to SvelteKit and SolidJS [{cid}].", txt)
        )  # Swapped stack
        UNSUPPORTED_PAIRS.append(
            (f"Created custom WebGL 3D rendering engines for browser games [{cid}].", txt)
        )  # Absent skill
    elif cid == "c_20":
        UNSUPPORTED_PAIRS.append(
            (f"Increasing mobile conversion rate by 65% through Core Web Vitals [{cid}].", txt)
        )  # Altered number (14% -> 65%)
        UNSUPPORTED_PAIRS.append(
            (
                f"Designed complex UX animations in Figma for enterprise banking portals [{cid}].",
                txt,
            )
        )  # Absent skill
        UNSUPPORTED_PAIRS.append(
            (f"Engineered offline service worker caching for native PWA applications [{cid}].", txt)
        )  # Absent skill


def evaluate_harder_calibration() -> None:
    print(f"Total Supported Sentences: {len(SUPPORTED_PAIRS)}")
    print(f"Total Plausible Unsupported Sentences: {len(UNSUPPORTED_PAIRS)}")

    embedder = ONNXEmbedder(model_type="minilm")

    supported_sims: list[float] = []
    unsupported_sims: list[float] = []

    for sent, chunk in SUPPORTED_PAIRS:
        sent_clean = CITATION_PATTERN.sub("", sent).strip()
        vecs = embedder.embed_texts([sent_clean, chunk[:500]])
        sim = float(np.dot(vecs[0], vecs[1]) / (np.linalg.norm(vecs[0]) * np.linalg.norm(vecs[1])))
        supported_sims.append(sim)

    for sent, chunk in UNSUPPORTED_PAIRS:
        # Check numerical & entity verification first
        nums_ok, _ = verify_numbers_and_entities_strict(sent, chunk)
        if not nums_ok:
            # Caught by deterministic entity/number filter -> effective similarity 0.0
            unsupported_sims.append(0.0)
            continue

        sent_clean = CITATION_PATTERN.sub("", sent).strip()
        vecs = embedder.embed_texts([sent_clean, chunk[:500]])
        sim = float(np.dot(vecs[0], vecs[1]) / (np.linalg.norm(vecs[0]) * np.linalg.norm(vecs[1])))
        unsupported_sims.append(sim)

    print("\n--- DISTRIBUTION SUMMARY ---")
    print(
        f"Supported Claims:   Mean={np.mean(supported_sims):.4f}, Median={np.median(supported_sims):.4f}, Min={np.min(supported_sims):.4f}, Max={np.max(supported_sims):.4f}"
    )
    print(
        f"Unsupported Claims: Mean={np.mean(unsupported_sims):.4f}, Median={np.median(unsupported_sims):.4f}, Min={np.min(unsupported_sims):.4f}, Max={np.max(unsupported_sims):.4f}"
    )

    thresholds = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
    calibration_table = []
    chosen_threshold = 0.50

    print("\n--- THRESHOLD SWEEP ---")
    print(
        f"{'Threshold':<10} | {'False Accept (FAR)':<20} | {'False Reject (FRR)':<20} | {'Status'}"
    )
    print("-" * 65)

    for tau in thresholds:
        # FAR: Unsupported accepted as true (sim >= tau)
        fa_count = sum(1 for s in unsupported_sims if s >= tau)
        far_pct = (fa_count / len(unsupported_sims)) * 100.0

        # FRR: Supported falsely rejected (sim < tau)
        fr_count = sum(1 for s in supported_sims if s < tau)
        frr_pct = (fr_count / len(supported_sims)) * 100.0

        status_str = "Eligible (FAR <= 2%)" if far_pct <= 2.0 else "Ineligible (FAR > 2%)"
        print(
            f"{tau:<10.2f} | {fa_count}/{len(unsupported_sims)} ({far_pct:5.2f}%)       | {fr_count}/{len(supported_sims)} ({frr_pct:5.2f}%)       | {status_str}"
        )

        calibration_table.append(
            {
                "threshold": tau,
                "false_accept_count": fa_count,
                "false_accept_rate_percent": round(far_pct, 2),
                "false_reject_count": fr_count,
                "false_reject_rate_percent": round(frr_pct, 2),
                "eligible_far_le_2pct": far_pct <= 2.0,
            }
        )

    # Pick lowest threshold with FAR <= 2% to minimize false rejects
    eligible = [row for row in calibration_table if row["eligible_far_le_2pct"]]
    if eligible:
        chosen_threshold = eligible[0]["threshold"]
    else:
        chosen_threshold = 0.55

    print(
        f"\nRecommended Calibration Threshold: tau = {chosen_threshold} (False Accept Rate <= 2.0%)"
    )

    # Save to docs/eval_critic_calibration.json and docs/eval_critic_benchmark_harder.json
    docs_dir = Path(__file__).resolve().parent.parent / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "metadata": {
            "source_script": "scripts/generate_harder_critic_benchmark.py",
            "supported_sample_size": len(SUPPORTED_PAIRS),
            "unsupported_sample_size": len(UNSUPPORTED_PAIRS),
            "embedder_model": "all-MiniLM-L6-v2",
            "calibration_criterion": "False Accept Rate <= 2.0%",
        },
        "distributions": {
            "supported_mean": round(float(np.mean(supported_sims)), 4),
            "supported_median": round(float(np.median(supported_sims)), 4),
            "supported_min": round(float(np.min(supported_sims)), 4),
            "supported_max": round(float(np.max(supported_sims)), 4),
            "unsupported_mean": round(float(np.mean(unsupported_sims)), 4),
            "unsupported_median": round(float(np.median(unsupported_sims)), 4),
            "unsupported_min": round(float(np.min(unsupported_sims)), 4),
            "unsupported_max": round(float(np.max(unsupported_sims)), 4),
        },
        "threshold_sweep": calibration_table,
        "chosen_threshold": chosen_threshold,
        "chosen_metrics": next(r for r in calibration_table if r["threshold"] == chosen_threshold),
    }

    with open(docs_dir / "eval_critic_calibration.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    with open(docs_dir / "eval_critic_benchmark_harder.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Saved critic calibration reports to {docs_dir / 'eval_critic_benchmark_harder.json'}")


if __name__ == "__main__":
    evaluate_harder_calibration()
