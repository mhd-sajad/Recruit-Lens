export interface JobItem {
  id: string;
  title: string;
  department: string;
  status: "Active" | "Closed" | "Draft" | "Ingesting";
  created_at: string;
  applicants_count: number;
  top_score: number;
  top_tier: "FastTrack" | "Interview" | "Hold" | "Reject";
  tier_counts: {
    fasttrack: number;
    interview: number;
    hold: number;
    reject: number;
  };
  raw_text?: string;
  is_ingesting?: boolean;
  ingest_progress?: {
    current: number;
    total: number;
  };
}

export interface CandidateItem {
  id: string;
  job_id?: string;
  code: string; // e.g. "6299" -> "Candidate #6299"
  name: string;
  email: string;
  location: string;
  most_recent_role: string; // Title only, zero company name!
  match_score: number;
  tier: "FastTrack" | "Interview" | "Hold" | "Reject";
  must_have_coverage: string; // e.g. "7 / 7"
  verified_experience: string; // e.g. "8.5 yrs" or "Dates missing"
  stage: "Screened" | "Interview" | "Technical assessment" | "Offer";
  missing_must_haves: string[];
  skills?: string[];
  raw_text?: string;
}

export interface CitationItem {
  id: string; // "c_01"
  text_snippet: string;
  char_start: number;
  char_end: number;
  section: string;
}

export interface CandidateDossier {
  candidate: CandidateItem;
  score_contributions: Array<{
    feature: string;
    delta: number;
    description: string;
  }>;
  skills: {
    matched: string[];
    inferred: string[];
    missing: string[];
  };
  briefing: {
    sentences: Array<{
      text: string;
      citation_ids: string[];
    }>;
  };
  resume_text: string;
  citations: CitationItem[];
  simulator_options: Array<{
    id: string;
    label: string;
    delta: number;
  }>;
  interview_questions: {
    skill_verification: Array<{
      question: string;
      target_skill: string;
      evaluation_criteria: string;
    }>;
    gap_probing: Array<{
      question: string;
      target_gap: string;
      evaluation_criteria: string;
    }>;
  };
}

export interface EmailDraftItem {
  id: string;
  type: "interview" | "hold" | "rejection";
  title: string;
  to_candidate_name: string;
  to_candidate_code: string;
  to_candidate_email: string;
  ai_draft: string;
  user_edit: string;
  is_approved: boolean;
  approved_at?: string;
  is_sent: boolean;
  sent_at?: string;
  is_dry_run: boolean;
}

export interface AuditEventItem {
  id: string;
  time: string;
  timestamp?: string;
  actor: string;
  action_badge: string;
  action_suffix?: string;
  badge_class: "e" | "i" | "h" | "r";
  target: string;
  detail: string;
}

// 1. Initial 3 Requisitions
export const INITIAL_JOBS: JobItem[] = [
  {
    id: "job-backend",
    title: "Staff Backend Engineer – Distributed Systems",
    department: "Core Infrastructure",
    status: "Active",
    created_at: "2026-10-15",
    applicants_count: 14,
    top_score: 95,
    top_tier: "FastTrack",
    tier_counts: {
      fasttrack: 3,
      interview: 4,
      hold: 4,
      reject: 3,
    },
    raw_text:
      "Seeking a Staff Backend Engineer to scale real-time distributed data pipelines. Must-have: Python or Go, Kafka or RabbitMQ, Distributed consensus, Docker, AWS, 6+ years experience. Education: Bachelor's in CS or equivalent.",
  },
  {
    id: "job-ml",
    title: "Senior ML Engineer – Search & NLP",
    department: "AI Research & Retrieval",
    status: "Active",
    created_at: "2026-10-18",
    applicants_count: 8,
    top_score: 82,
    top_tier: "Interview",
    tier_counts: {
      fasttrack: 0,
      interview: 4,
      hold: 3,
      reject: 1,
    },
    raw_text:
      "Seeking Senior ML Engineer with deep expertise in dense embeddings, BM25 hybrid reranking, PyTorch, and ONNX runtime optimization. 5+ years experience.",
  },
  {
    id: "job-security",
    title: "Staff Security Engineer – Cloud Infra",
    department: "Security & Trust",
    status: "Draft",
    created_at: "2026-10-24",
    applicants_count: 0,
    top_score: 0,
    top_tier: "Hold",
    tier_counts: {
      fasttrack: 0,
      interview: 0,
      hold: 0,
      reject: 0,
    },
    raw_text: "",
  },
];

// 2. 14 Candidates for Staff Backend Engineer
export const MOCK_CANDIDATES: CandidateItem[] = [
  {
    id: "cand-6299",
    job_id: "job-backend",
    code: "6299",
    name: "Alex Rivera",
    email: "alex.rivera@engineering.io",
    location: "San Francisco, CA",
    most_recent_role: "Staff Distributed Systems Architect",
    match_score: 95,
    tier: "FastTrack",
    must_have_coverage: "7 / 7",
    verified_experience: "8.5 yrs",
    stage: "Interview",
    missing_must_haves: [],
  },
  {
    id: "cand-8412",
    job_id: "job-backend",
    code: "8412",
    name: "Elena Rostova",
    email: "elena.rostova@cloudscale.net",
    location: "Austin, TX",
    most_recent_role: "Lead Platform Infrastructure Engineer",
    match_score: 91,
    tier: "FastTrack",
    must_have_coverage: "7 / 7",
    verified_experience: "7.0 yrs",
    stage: "Technical assessment",
    missing_must_haves: [],
  },
  {
    id: "cand-7721",
    job_id: "job-backend",
    code: "7721",
    name: "Marcus Vance",
    email: "mvance@distributed.org",
    location: "Seattle, WA",
    most_recent_role: "Senior Backend Core Engineer",
    match_score: 88,
    tier: "FastTrack",
    must_have_coverage: "6 / 7",
    verified_experience: "6.2 yrs",
    stage: "Screened",
    missing_must_haves: ["Cassandra"],
  },
  {
    id: "cand-5304",
    job_id: "job-backend",
    code: "5304",
    name: "Priya Sharma",
    email: "psharma@techsystems.co",
    location: "New York, NY",
    most_recent_role: "Senior Systems Engineer",
    match_score: 82,
    tier: "Interview",
    must_have_coverage: "6 / 7",
    verified_experience: "5.5 yrs",
    stage: "Screened",
    missing_must_haves: ["Raft Consensus"],
  },
  {
    id: "cand-9102",
    job_id: "job-backend",
    code: "9102",
    name: "Devon Clark",
    email: "dclark@cloudbackend.dev",
    location: "Boston, MA",
    most_recent_role: "Backend Services Engineer",
    match_score: 79,
    tier: "Interview",
    must_have_coverage: "5 / 7",
    verified_experience: "5.0 yrs",
    stage: "Screened",
    missing_must_haves: ["Kafka Streaming"],
  },
  {
    id: "cand-4431",
    job_id: "job-backend",
    code: "4431",
    name: "Hannah Schmidt",
    email: "hannah.s@inframesh.eu",
    location: "Chicago, IL",
    most_recent_role: "Distributed Services Developer",
    match_score: 76,
    tier: "Interview",
    must_have_coverage: "5 / 7",
    verified_experience: "4.8 yrs",
    stage: "Screened",
    missing_must_haves: ["Kubernetes"],
  },
  {
    id: "cand-3290",
    job_id: "job-backend",
    code: "3290",
    name: "Tariq Mansoor",
    email: "tmansoor@cloudnet.org",
    location: "San Jose, CA",
    most_recent_role: "Cloud Software Engineer",
    match_score: 73,
    tier: "Interview",
    must_have_coverage: "5 / 7",
    verified_experience: "4.5 yrs",
    stage: "Screened",
    missing_must_haves: ["Go Depth"],
  },
  {
    id: "cand-1845",
    job_id: "job-backend",
    code: "1845",
    name: "Rachel Chen",
    email: "rchen@dataflow.tech",
    location: "Denver, CO",
    most_recent_role: "Software Engineer III",
    match_score: 68,
    tier: "Hold",
    must_have_coverage: "4 / 7",
    verified_experience: "3.5 yrs",
    stage: "Screened",
    missing_must_haves: ["Distributed consensus", "6+ yrs exp"],
  },
  {
    id: "cand-2981",
    job_id: "job-backend",
    code: "2981",
    name: "Jordan Miller",
    email: "jmiller@asyncapi.io",
    location: "Portland, OR",
    most_recent_role: "Full Stack Backend Specialist",
    match_score: 65,
    tier: "Hold",
    must_have_coverage: "4 / 7",
    verified_experience: "Dates missing",
    stage: "Screened",
    missing_must_haves: ["Kafka", "AWS Architecture"],
  },
  {
    id: "cand-6619",
    job_id: "job-backend",
    code: "6619",
    name: "Siddharth Nair",
    email: "snair@microservices.in",
    location: "Atlanta, GA",
    most_recent_role: "Application Backend Developer",
    match_score: 62,
    tier: "Hold",
    must_have_coverage: "4 / 7",
    verified_experience: "3.0 yrs",
    stage: "Screened",
    missing_must_haves: ["Distributed consensus", "Go"],
  },
  {
    id: "cand-7110",
    job_id: "job-backend",
    code: "7110",
    name: "Chloe Dubois",
    email: "cdubois@queuesystems.ca",
    location: "Montreal, QC",
    most_recent_role: "Software Developer",
    match_score: 59,
    tier: "Hold",
    must_have_coverage: "3 / 7",
    verified_experience: "2.8 yrs",
    stage: "Screened",
    missing_must_haves: ["Kafka", "Docker", "Consensus"],
  },
  {
    id: "cand-9832",
    job_id: "job-backend",
    code: "9832",
    name: "Kevin Ortiz",
    email: "kortiz@devbootcamp.io",
    location: "Miami, FL",
    most_recent_role: "Junior Backend Developer",
    match_score: 48,
    tier: "Reject",
    must_have_coverage: "2 / 7",
    verified_experience: "1.2 yrs",
    stage: "Screened",
    missing_must_haves: ["6+ yrs exp", "Kafka", "Consensus", "AWS"],
  },
  {
    id: "cand-1209",
    job_id: "job-backend",
    code: "1209",
    name: "Amina Al-Hassan",
    email: "amina.h@webapps.net",
    location: "Dallas, TX",
    most_recent_role: "Frontend & API Web Developer",
    match_score: 41,
    tier: "Reject",
    must_have_coverage: "1 / 7",
    verified_experience: "1.0 yrs",
    stage: "Screened",
    missing_must_haves: ["Python depth", "Distributed systems", "Kafka", "AWS"],
  },
  {
    id: "cand-5541",
    job_id: "job-backend",
    code: "5541",
    name: "Lucas Pereira",
    email: "lpereira@scripting.org",
    location: "Phoenix, AZ",
    most_recent_role: "IT Automation Scripting Specialist",
    match_score: 35,
    tier: "Reject",
    must_have_coverage: "1 / 7",
    verified_experience: "Dates missing",
    stage: "Screened",
    missing_must_haves: ["Backend Architecture", "Kafka", "Go", "Consensus"],
  },
];

// 3. Full Verified Evidence Dossier for Candidate #6299 (Alex Rivera)
const FULL_RESUME_TEXT = `EXECUTIVE SUMMARY
Staff Distributed Systems Architect with 8.5 years of verifiable experience designing and maintaining fault-tolerant, high-concurrency microservice platforms in Python and Go. Proven track record leading infrastructure transformations and streaming architectures.

CORE SKILLS & TECHNOLOGIES
Languages: Python (Asyncio, FastAPI, PyTorch), Go (Goroutines, Channels), SQL, Bash
Distributed Systems: Apache Kafka, Redis, RabbitMQ, Raft consensus protocols, gRPC, Protobuf
Cloud & Orchestration: Kubernetes, Docker, AWS (ECS, EKS, RDS, DynamoDB, S3, CloudWatch)
Databases & Storage: PostgreSQL, Redis Cluster, Elasticsearch, S3

PROFESSIONAL EXPERIENCE
Staff Distributed Systems Architect | 2021 - Present
- Architected and led the complete migration of core asynchronous event streaming from RabbitMQ to Apache Kafka, processing 120,000 events/sec with 99.99% availability across 4 geographical regions.
- Implemented high-throughput distributed locking and consensus coordinator routines in Go utilizing Raft-backed leader election, reducing transaction race failures to zero.
- Managed Kubernetes container cluster orchestration across 40+ production microservices on AWS EKS, optimizing auto-scaling policies to decrease cloud infrastructure costs by 28%.
- Championed engineering excellence, establishing weekly resilience game days, automated chaos testing, and directly mentoring 6 senior backend engineers.

Senior Infrastructure Engineer | 2018 - 2021
- Built high-speed distributed caching layers using Redis Cluster, reducing 95th percentile database read latency from 145ms to 8ms for 4M daily active users.
- Designed gRPC microservices in Python and Go with bidirectional streaming APIs, achieving 3x throughput over legacy REST endpoints.
- Authored production Terraform modules and CI/CD pipelines deploying Docker microservices with zero downtime rolling updates.

Software Engineer – Backend | 2015 - 2018
- Developed core RESTful APIs in Python using PostgreSQL and SQLAlchemy with strict relational indexing and connection pooling.
- Designed background task worker queues processing asynchronous data imports and report generation.

EDUCATION & CERTIFICATIONS
Bachelor of Science in Computer Science | University of California, Berkeley | 2011 - 2015
AWS Certified Solutions Architect – Professional`;

export const FULL_DOSSIER_CANDIDATE: CandidateDossier = {
  candidate: MOCK_CANDIDATES[0]!,
  score_contributions: [
    {
      feature: "Python & Go language mastery",
      delta: 24,
      description: "Extensive production usage across concurrency and async architectures",
    },
    {
      feature: "Distributed streaming & consensus (Kafka/Raft)",
      delta: 22,
      description: "Direct experience with 120k events/sec throughput and Raft leader election",
    },
    {
      feature: "AWS & Kubernetes infrastructure",
      delta: 18,
      description: "Orchestration across 40+ microservices on AWS EKS",
    },
    {
      feature: "Verified experience depth (8.5 yrs vs 6.0 req)",
      delta: 14,
      description: "Exceeds minimum experience requirement by 2.5 years",
    },
    {
      feature: "Microservices & gRPC performance",
      delta: 12,
      description: "Reduced p95 latency to 8ms and increased throughput 3x",
    },
    {
      feature: "Lack of direct Cassandra experience",
      delta: -5,
      description: "JD lists Cassandra as desirable secondary storage backend",
    },
  ],
  skills: {
    matched: [
      "python",
      "go",
      "kafka",
      "distributed systems",
      "redis",
      "postgresql",
      "docker",
      "aws",
      "raft consensus",
      "grpc",
    ],
    inferred: [
      "system design",
      "microservices architecture",
      "concurrency",
      "load balancing",
      "ci/cd pipeline",
      "performance tuning",
    ],
    missing: ["cassandra", "istio"],
  },
  briefing: {
    sentences: [
      {
        text: "Candidate brings 8.5 years of verifiable experience architecting high-throughput distributed systems in Python and Go.",
        citation_ids: ["c_01"],
      },
      {
        text: "Led end-to-end migration of messaging infrastructure to Apache Kafka, processing 120,000 events/sec with 99.99% availability.",
        citation_ids: ["c_02"],
      },
      {
        text: "Demonstrated advanced Kubernetes and AWS container orchestration across 40+ microservices on AWS EKS.",
        citation_ids: ["c_03"],
      },
      {
        text: "Solid academic foundation with a Bachelor of Science in Computer Science, but lacks explicit production Cassandra evidence.",
        citation_ids: ["c_04"],
      },
      {
        text: "Demonstrated technical leadership mentoring 6 senior engineers and driving cross-team resilience game days.",
        citation_ids: ["c_05"],
      },
    ],
  },
  resume_text: FULL_RESUME_TEXT,
  citations: [
    {
      id: "c_01",
      section: "EXECUTIVE SUMMARY",
      text_snippet:
        "Staff Distributed Systems Architect with 8.5 years of verifiable experience designing and maintaining fault-tolerant, high-concurrency microservice platforms in Python and Go.",
      char_start: 20,
      char_end: 187,
    },
    {
      id: "c_02",
      section: "PROFESSIONAL EXPERIENCE",
      text_snippet:
        "Architected and led the complete migration of core asynchronous event streaming from RabbitMQ to Apache Kafka, processing 120,000 events/sec with 99.99% availability across 4 geographical regions.",
      char_start: 649,
      char_end: 847,
    },
    {
      id: "c_03",
      section: "PROFESSIONAL EXPERIENCE",
      text_snippet:
        "Managed Kubernetes container cluster orchestration across 40+ production microservices on AWS EKS, optimizing auto-scaling policies to decrease cloud infrastructure costs by 28%.",
      char_start: 1009,
      char_end: 1189,
    },
    {
      id: "c_04",
      section: "EDUCATION & CERTIFICATIONS",
      text_snippet:
        "Bachelor of Science in Computer Science | University of California, Berkeley | 2011 - 2015",
      char_start: 1947,
      char_end: 2038,
    },
    {
      id: "c_05",
      section: "PROFESSIONAL EXPERIENCE",
      text_snippet:
        "Championed engineering excellence, establishing weekly resilience game days, automated chaos testing, and directly mentoring 6 senior backend engineers.",
      char_start: 1192,
      char_end: 1349,
    },
  ],
  simulator_options: [
    {
      id: "opt-cassandra",
      label: "Cassandra depth (demonstrates NoSQL distributed storage)",
      delta: 3,
    },
    {
      id: "opt-istio",
      label: "Istio Service Mesh routing experience",
      delta: 2,
    },
    {
      id: "opt-experience",
      label: "+1 Year additional Staff-level experience",
      delta: 1,
    },
  ],
  interview_questions: {
    skill_verification: [
      {
        question:
          "Can you walk through how you partitioned Kafka topics during your migration to handle 120,000 events/sec without head-of-line consumer blocking?",
        target_skill: "Apache Kafka Streaming",
        evaluation_criteria:
          "Candidate explains partition key strategy, consumer group balancing, and lag monitoring without deadlocks.",
      },
      {
        question:
          "Describe how your Go Raft consensus implementation handles network partitions between the primary region and isolated follower nodes.",
        target_skill: "Raft Consensus & Distributed Locking",
        evaluation_criteria:
          "Candidate demonstrates understanding of term counters, split-brain avoidance, and quorum heartbeats.",
      },
      {
        question:
          "How did you tune Kubernetes horizontal pod autoscaling and resource limits on AWS EKS to achieve a 28% infrastructure cost reduction?",
        target_skill: "Kubernetes & AWS EKS",
        evaluation_criteria:
          "Candidate explains memory/CPU request sizing, cluster autoscaler metrics, and pod disruption budgets.",
      },
    ],
    gap_probing: [
      {
        question:
          "Since your recent architecture centered on PostgreSQL and Redis, how would you approach Cassandra wide-column data modeling and tombstone management if tasked with building our high-volume audit logs?",
        target_gap: "Cassandra NoSQL Storage",
        evaluation_criteria:
          "Candidate articulates understanding of partition keys, clustering columns, query-driven modeling, and write amplification.",
      },
      {
        question:
          "How do you manage mutual TLS and distributed tracing across 40+ microservices without a dedicated service mesh like Istio?",
        target_gap: "Service Mesh & mTLS",
        evaluation_criteria:
          "Candidate discusses gRPC interceptors, OpenTelemetry propagation, and certificate rotation tradeoffs.",
      },
    ],
  },
};

// 4. Three Email Drafts (Interview, Hold, Score-Free Rejection)
export const INITIAL_EMAILS: EmailDraftItem[] = [
  {
    id: "email-01",
    type: "interview",
    title: "Interview Invitation: Staff Backend Engineer – Distributed Systems",
    to_candidate_name: "Alex Rivera",
    to_candidate_code: "6299",
    to_candidate_email: "alex.rivera@engineering.io",
    ai_draft: `Dear Alex,\n\nThank you for your application for the Staff Backend Engineer – Distributed Systems position. Our engineering team was very impressed by your extensive background in distributed systems architecture, particularly your hands-on work with Apache Kafka streaming and high-throughput Go services.\n\nWe would love to invite you to an initial 45-minute technical conversation with our Engineering Director to discuss your experience and share more about the distributed scaling challenges our team is currently tackling.\n\nPlease let us know your availability over the next few business days.\n\nBest regards,\nRecruit Lens Talent Team`,
    user_edit: `Dear Alex,\n\nThank you for your application for the Staff Backend Engineer – Distributed Systems position. Our engineering team was very impressed by your extensive background in distributed systems architecture, particularly your hands-on work with Apache Kafka streaming and high-throughput Go services.\n\nWe would love to invite you to an initial 45-minute technical conversation with our Engineering Director to discuss your experience and share more about the distributed scaling challenges our team is currently tackling.\n\nPlease let us know your availability over the next few business days.\n\nBest regards,\nRecruit Lens Talent Team`,
    is_approved: false,
    is_sent: false,
    is_dry_run: true,
  },
  {
    id: "email-02",
    type: "hold",
    title: "Application Status Update: Staff Backend Engineer – Distributed Systems",
    to_candidate_name: "Rachel Chen",
    to_candidate_code: "1845",
    to_candidate_email: "rchen@dataflow.tech",
    ai_draft: `Dear Rachel,\n\nThank you for taking the time to share your experience with us for the Staff Backend Engineer position.\n\nWe have reviewed your background and were impressed by your backend engineering foundation and API design work. At present, we are in active conversations with candidates whose immediate experience aligns closer to our 6+ year distributed consensus requirement, but we would like to keep your profile active in our pool as our team expands in the upcoming quarter.\n\nWe will reach out as soon as a fitting requisition opens.\n\nSincerely,\nRecruit Lens Talent Team`,
    user_edit: `Dear Rachel,\n\nThank you for taking the time to share your experience with us for the Staff Backend Engineer position.\n\nWe have reviewed your background and were impressed by your backend engineering foundation and API design work. At present, we are in active conversations with candidates whose immediate experience aligns closer to our 6+ year distributed consensus requirement, but we would like to keep your profile active in our pool as our team expands in the upcoming quarter.\n\nWe will reach out as soon as a fitting requisition opens.\n\nSincerely,\nRecruit Lens Talent Team`,
    is_approved: true,
    approved_at: "2026-10-28 14:10 UTC",
    is_sent: false,
    is_dry_run: true,
  },
  {
    id: "email-03",
    type: "rejection",
    title: "Update regarding your application: Staff Backend Engineer – Distributed Systems",
    to_candidate_name: "Kevin Ortiz",
    to_candidate_code: "9832",
    to_candidate_email: "kortiz@devbootcamp.io",
    // NON-NEGOTIABLE RULE: Absolutely NO scores or numbers in rejection email!
    ai_draft: `Dear Kevin,\n\nThank you for your interest in joining our team and for taking the time to submit your application for the Staff Backend Engineer – Distributed Systems position.\n\nAfter careful consideration of our current architectural priorities, we have decided to move forward with candidates whose backgrounds demonstrate deeper senior-level experience in large-scale distributed consensus protocols and cloud infrastructure management.\n\nWe appreciate the time you invested in exploring opportunities with Recruit Lens and wish you every success in your professional endeavors.\n\nSincerely,\nRecruit Lens Hiring Team`,
    user_edit: `Dear Kevin,\n\nThank you for your interest in joining our team and for taking the time to submit your application for the Staff Backend Engineer – Distributed Systems position.\n\nAfter careful consideration of our current architectural priorities, we have decided to move forward with candidates whose backgrounds demonstrate deeper senior-level experience in large-scale distributed consensus protocols and cloud infrastructure management.\n\nWe appreciate the time you invested in exploring opportunities with Recruit Lens and wish you every success in your professional endeavors.\n\nSincerely,\nRecruit Lens Hiring Team`,
    is_approved: false,
    is_sent: false,
    is_dry_run: true,
  },
];

// 5. Initial Immutable Audit Trail Entries (matching approved Audit Log design)
export const INITIAL_AUDIT_LOGS: AuditEventItem[] = [
  {
    id: "aud-001",
    time: "10:42:07",
    timestamp: "2026-10-30 10:42:07 UTC",
    actor: "R. Iyer",
    action_badge: "Blind mode",
    action_suffix: " enabled",
    badge_class: "i",
    target: "Global setting",
    detail: "Default for new sessions: off",
  },
  {
    id: "aud-002",
    time: "10:44:31",
    timestamp: "2026-10-30 10:44:31 UTC",
    actor: "R. Iyer",
    action_badge: "Tier override",
    badge_class: "h",
    target: "Candidate #6299",
    detail: "Hold → Interview · reason: strong FastAPI evidence [c_01]",
  },
  {
    id: "aud-003",
    time: "10:51:12",
    timestamp: "2026-10-30 10:51:12 UTC",
    actor: "R. Iyer",
    action_badge: "Draft approved",
    badge_class: "e",
    target: "Interview Invite · #6299",
    detail: "Approved by R. Iyer · dry-run",
  },
  {
    id: "aud-004",
    time: "10:52:40",
    timestamp: "2026-10-30 10:52:40 UTC",
    actor: "R. Iyer",
    action_badge: "Approval revoked",
    badge_class: "r",
    target: "Interview Invite · #6299",
    detail: "Draft edited after approval",
  },
  {
    id: "aud-005",
    time: "10:55:03",
    timestamp: "2026-10-30 10:55:03 UTC",
    actor: "System",
    action_badge: "Email sent",
    badge_class: "i",
    target: "Interview Invite · #6299",
    detail: "Dry-run · no message delivered",
  },
  {
    id: "aud-006",
    time: "11:02:19",
    timestamp: "2026-10-30 11:02:19 UTC",
    actor: "System",
    action_badge: "CVs indexed",
    badge_class: "i",
    target: "Staff Backend Engineer",
    detail: "14 resumes · 0 failed",
  },
];

// Convenient aliases
export const INITIAL_CANDIDATES = MOCK_CANDIDATES;
export const SAMPLE_DOSSIER_6299 = FULL_DOSSIER_CANDIDATE;

export const MOCK_ML_CANDIDATES: CandidateItem[] = [
  {
    id: "cand-ml-1",
    job_id: "job-ml",
    code: "4190",
    name: "Dr. Marcus Vance",
    email: "marcus.vance@vectorflow.ai",
    location: "Seattle, WA",
    most_recent_role: "Staff Machine Learning Scientist",
    match_score: 82,
    tier: "Interview",
    must_have_coverage: "6 / 6",
    verified_experience: "7.0 yrs",
    stage: "Screened",
    missing_must_haves: [],
  },
  {
    id: "cand-ml-2",
    job_id: "job-ml",
    code: "7741",
    name: "Siddharth Rao",
    email: "sid.rao@tensorlab.io",
    location: "New York, NY",
    most_recent_role: "Senior NLP Research Engineer",
    match_score: 79,
    tier: "Interview",
    must_have_coverage: "5 / 6",
    verified_experience: "5.5 yrs",
    stage: "Interview",
    missing_must_haves: ["ONNX Runtime"],
  },
];

export const ALL_MOCK_CANDIDATES: CandidateItem[] = [
  ...MOCK_CANDIDATES,
  ...MOCK_ML_CANDIDATES,
];

export function getCandidatesForJob(jobId: string, customList?: CandidateItem[]): CandidateItem[] {
  const pool = customList && customList.length > 0 ? customList : ALL_MOCK_CANDIDATES;
  return pool.filter((c) => (c.job_id || "job-backend") === jobId);
}

export function getCandidateById(candidateId: string, jobId?: string, customList?: CandidateItem[]): CandidateItem | undefined {
  const pool = customList && customList.length > 0 ? customList : ALL_MOCK_CANDIDATES;
  const found = pool.find((c) => c.id === candidateId || c.code === candidateId);
  if (!found) return undefined;
  if (jobId && found.job_id && found.job_id !== jobId) {
    return undefined; // candidate belongs to another job!
  }
  return found;
}
