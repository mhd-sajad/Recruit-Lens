import type { JobResponse, EvaluationSummaryResponse } from "../types/api";
import type { JobItem, CandidateItem } from "./mockData";

export function jobResponseToJobItem(
  job: JobResponse,
  candidatesCount: number = 0,
  candidateEvals: EvaluationSummaryResponse[] = []
): JobItem {
  let fasttrack = 0;
  let interview = 0;
  let hold = 0;
  let reject = 0;
  let maxScore = 0;
  let topTier: "FastTrack" | "Interview" | "Hold" | "Reject" = "FastTrack";

  if (candidateEvals.length > 0) {
    candidateEvals.forEach((c) => {
      const score = Math.round(c.total_score >= 1 ? c.total_score : c.total_score * 100);
      if (score > maxScore) maxScore = score;

      const t = (c.tier || "").toLowerCase();
      if (t.includes("fasttrack") || t.includes("strong")) {
        fasttrack++;
        topTier = "FastTrack";
      } else if (t.includes("interview") || t.includes("review")) {
        interview++;
        if (topTier !== "FastTrack") topTier = "Interview";
      } else if (t.includes("hold")) {
        hold++;
        if (topTier !== "FastTrack" && topTier !== "Interview") topTier = "Hold";
      } else {
        reject++;
        if (topTier !== "FastTrack" && topTier !== "Interview" && topTier !== "Hold") topTier = "Reject";
      }
    });
  } else if (job.id === "job-backend") {
    // Only the demo workspace job has initial counts before real evaluations load
    fasttrack = 3;
    interview = 4;
    hold = 4;
    reject = 3;
    maxScore = 95;
    topTier = "FastTrack";
  } else {
    // Newly created requisitions start strictly with 0 until candidates are processed
    fasttrack = 0;
    interview = 0;
    hold = 0;
    reject = 0;
    maxScore = 0;
    topTier = "Hold";
  }

  const createdDate = new Date(job.created_at);
  const now = new Date();
  const diffDays = Math.max(0, Math.floor((now.getTime() - createdDate.getTime()) / (1000 * 3600 * 24)));
  const relativeDate = diffDays === 0 ? "today" : `${diffDays}d ago`;

  return {
    id: job.id,
    title: job.title,
    department: job.department || "Engineering",
    status: job.status === "active" ? "Active" : job.status === "closed" ? "Closed" : "Draft",
    created_at: `Created ${relativeDate}`,
    applicants_count: candidatesCount || candidateEvals.length || (job.id === "job-backend" ? 14 : 0),
    top_score: maxScore,
    top_tier: topTier,
    tier_counts: {
      fasttrack,
      interview,
      hold,
      reject,
    },
    raw_text: job.raw_text,
  };
}

export function evaluationSummaryToCandidateItem(
  e: EvaluationSummaryResponse,
  index: number = 0
): CandidateItem {
  const score = Math.round(e.total_score >= 1 ? e.total_score : e.total_score * 100);
  const t = (e.tier || "").toLowerCase();
  let tier: "FastTrack" | "Interview" | "Hold" | "Reject" = "Hold";
  if (t.includes("fasttrack") || t.includes("strong") || score >= 85) {
    tier = "FastTrack";
  } else if (t.includes("interview") || t.includes("review") || score >= 70) {
    tier = "Interview";
  } else if (t.includes("hold") || score >= 55) {
    tier = "Hold";
  } else {
    tier = "Reject";
  }

  const st = (e.stage || "").toLowerCase();
  let stage: CandidateItem["stage"] = "Screened";
  if (st.includes("interview")) stage = "Interview";
  else if (st.includes("tech") || st.includes("assessment")) stage = "Technical assessment";
  else if (st.includes("offer") || st.includes("hire")) stage = "Offer";

  // Deterministic 4-digit code
  const code = e.id ? e.id.replace(/-/g, "").slice(-4).toUpperCase() : `${6200 + index}`;

  const defaultTitles = [
    "Staff Backend Architect",
    "Senior Distributed Systems Engineer",
    "Cloud Infrastructure Engineer",
    "Principal Data Platform Lead",
    "Senior Microservices Engineer",
    "Backend Platform Specialist",
  ];

  const roleTitle = e.candidate_title || defaultTitles[index % defaultTitles.length] || "Backend Engineer";

  return {
    id: e.id,
    code,
    name: e.candidate_name || `Alex Rivera`,
    email: `cand-${code.toLowerCase()}@recruitlens.io`,
    location: "San Francisco, CA (Remote)",
    most_recent_role: roleTitle, // Zero company name!
    match_score: score,
    tier,
    must_have_coverage: tier === "FastTrack" ? "7 / 7" : tier === "Interview" ? "6 / 7" : "4 / 7",
    verified_experience:
      e.years_experience !== null && e.years_experience !== undefined && e.years_experience > 0
        ? `${e.years_experience.toFixed(1)} yrs`
        : "8.5 yrs",
    stage,
    missing_must_haves: e.missing_must_haves || (tier === "Reject" ? ["Cassandra", "Raft"] : []),
  };
}
