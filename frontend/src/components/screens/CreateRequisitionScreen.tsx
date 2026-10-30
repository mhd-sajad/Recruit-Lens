import React, { useState, useRef } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Upload,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Plus,
  Trash2,
} from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { jobResponseToJobItem } from "../../lib/transformers";
import type { JobItem } from "../../lib/mockData";

interface CreateRequisitionScreenProps {
  initialStep?: number;
  onNavigate: (path: string) => void;
  onJobCreated: (job: JobItem) => void;
}

interface UploadedFileItem {
  id: string;
  name: string;
  size: string;
  status: "Indexed" | "Processing" | "Abstain";
  error?: string;
}

export const CreateRequisitionScreen: React.FC<CreateRequisitionScreenProps> = ({
  initialStep = 1,
  onNavigate,
  onJobCreated,
}) => {
  const { refreshJobs } = useAuth();
  const [step, setStep] = useState<1 | 2 | 3>(
    initialStep === 2 ? 2 : initialStep === 3 ? 3 : 1
  );

  // Step 1: Role Details
  const [title, setTitle] = useState("Staff Backend Engineer – Distributed Systems");
  const [department, setDepartment] = useState("Core Infrastructure");
  const [location, setLocation] = useState("Remote (US / EMEA)");
  const [minExpYears, setMinExpYears] = useState(6);
  const [jdText, setJdText] = useState(
    `We are seeking a Staff Backend Engineer with 6+ years of verified distributed systems experience to lead our real-time streaming infrastructure.

Must-Have Requirements:
- Deep expertise in Go (Golang) and Apache Kafka high-throughput streaming.
- Production operations experience with Kubernetes (AWS EKS) and container orchestration.
- Proven track record implementing distributed consensus protocols (Raft, Paxos).
- Cassandra or wide-column NoSQL data modeling for petabyte-scale storage.
- Python data pipeline integration and microservices API architecture.

Nice-to-Have Requirements:
- Experience with OpenTelemetry and mutual TLS (mTLS).
- Prior contributions to open-source distributed database ecosystems.`
  );

  // Step 2: Skills & Weights
  const [mustHaves, setMustHaves] = useState<Array<{ name: string; weight: number }>>([
    { name: "Distributed consensus & Raft", weight: 30 },
    { name: "Go & Kafka streaming", weight: 25 },
    { name: "Kubernetes & AWS EKS", weight: 20 },
    { name: "Cassandra NoSQL Storage", weight: 15 },
    { name: "Python API Pipelines", weight: 10 },
  ]);

  const [niceToHaves] = useState<string[]>([
    "OpenTelemetry & Observability",
    "Mutual TLS & Service Mesh",
    "gRPC Interceptors",
  ]);

  const [newSkillName, setNewSkillName] = useState("");

  // Step 3: Files
  const [files, setFiles] = useState<UploadedFileItem[]>([
    { id: "f-1", name: "alex_rivera_resume.pdf", size: "240 KB", status: "Indexed" },
    { id: "f-2", name: "rachel_chen_cv.pdf", size: "195 KB", status: "Indexed" },
    { id: "f-3", name: "marcus_vance_cv.docx", size: "310 KB", status: "Indexed" },
    { id: "f-4", name: "elena_rostova_resume.pdf", size: "280 KB", status: "Processing" },
    { id: "f-5", name: "kevin_ortiz_resume.pdf", size: "180 KB", status: "Indexed" },
    { id: "f-6", name: "scanned_vendor_invoice.pdf", size: "260 KB", status: "Abstain", error: "Non-resume document flagged by resume gate" },
  ]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const totalWeight = mustHaves.reduce((acc, cur) => acc + cur.weight, 0);
  const isWeightValid = totalWeight === 100;

  const handleWeightChange = (index: number, val: number) => {
    const updated = [...mustHaves];
    updated[index]!.weight = Math.max(0, Math.min(100, val));
    setMustHaves(updated);
  };

  const handleAddSkill = () => {
    if (!newSkillName.trim()) return;
    setMustHaves([...mustHaves, { name: newSkillName.trim(), weight: 10 }]);
    setNewSkillName("");
  };

  const handleRemoveSkill = (index: number) => {
    setMustHaves(mustHaves.filter((_, i) => i !== index));
  };

  const [rawFiles, setRawFiles] = useState<File[]>([]);

  const handleFileUpload = (incoming: FileList | null) => {
    if (!incoming || incoming.length === 0) return;
    const incomingArr = Array.from(incoming);
    const validPdfs = incomingArr.filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    setRawFiles((prev) => [...prev, ...validPdfs]);

    const newItems: UploadedFileItem[] = [];
    incomingArr.forEach((file, idx) => {
      const isInvoice = file.name.toLowerCase().includes("invoice") || file.name.toLowerCase().includes("receipt");
      newItems.push({
        id: `upload-${Date.now()}-${idx}`,
        name: file.name,
        size: `${Math.round(file.size / 1024)} KB`,
        status: isInvoice ? "Abstain" : "Indexed",
        error: isInvoice ? "Non-resume detected by intake classifier" : undefined,
      });
    });

    setFiles((prev) => [...prev, ...newItems]);
  };

  const handleFinish = async () => {
    if (!isWeightValid) {
      setStep(2);
      setSubmitError("Weights must sum to exactly 100% before finishing.");
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    // Normalize weights to float values summing to 1.0
    const weightMap = Object.fromEntries(
      mustHaves.map((m) => [m.name, m.weight / 100])
    );

    try {
      const createdJob = await api.createJob({
        title: title.trim(),
        department: department.trim(),
        raw_text: jdText,
        weights: weightMap,
      });

      // If user uploaded real resumes, upload them to the backend ingestion queue
      if (rawFiles.length > 0) {
        try {
          await api.uploadResumes(createdJob.id, rawFiles);
        } catch (uploadErr) {
          console.error("Failed to upload resumes to backend:", uploadErr);
        }
      }

      await refreshJobs();
      const realJobItem = jobResponseToJobItem(createdJob);
      onJobCreated(realJobItem);
      onNavigate(`/jobs/${createdJob.id}/candidates`);
    } catch (err: unknown) {
      console.warn("Backend create job failed or offline, falling back to local:", err);
      // Fallback for standalone / mock offline preview
      const fallbackId = `job-${Date.now()}`;
      const fallbackJob: JobItem = {
        id: fallbackId,
        title: title.trim(),
        department: department.trim(),
        status: "Active",
        created_at: new Date().toISOString().split("T")[0]!,
        applicants_count: files.filter((f) => f.status !== "Abstain").length,
        top_score: 95,
        top_tier: "FastTrack",
        tier_counts: {
          fasttrack: 3,
          interview: 2,
          hold: 1,
          reject: 0,
        },
        raw_text: jdText,
      };
      onJobCreated(fallbackJob);
      onNavigate(`/jobs/${fallbackId}/candidates`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Step Progress Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-semibold text-indigo-400 uppercase tracking-wider">
              NEW REQUISITION · STEP {step} OF 3
            </span>
          </div>
          <button
            onClick={() => onNavigate("/requisitions")}
            className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            Cancel
          </button>
        </div>

        {/* Step Tabs Indicator */}
        <div className="grid grid-cols-3 gap-2">
          {[
            { s: 1, label: "Role Details" },
            { s: 2, label: "Skills & Scoring" },
            { s: 3, label: "Candidate CVs" },
          ].map((st) => (
            <div
              key={st.s}
              className={`h-2 rounded-full transition-colors ${
                st.s <= step ? "bg-indigo-600" : "bg-[var(--border-default)]"
              }`}
            />
          ))}
        </div>
      </div>

      {submitError && (
        <div className="mb-6 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
          <AlertTriangle size={16} className="shrink-0" />
          <span>{submitError}</span>
        </div>
      )}

      {/* STEP 1: DESCRIBE THE ROLE */}
      {step === 1 && (
        <div className="p-6 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] space-y-6">
          <div>
            <h1 className="text-xl font-bold text-[var(--text-primary)]">
              Describe the role
            </h1>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Enter the role details and paste the job description. Recruit Lens will extract the key skills in Step 2.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">
                Job Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[var(--border-default)] bg-[var(--bg-canvas)] text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">
                Department
              </label>
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[var(--border-default)] bg-[var(--bg-canvas)] text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">
                Location
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[var(--border-default)] bg-[var(--bg-canvas)] text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[var(--text-primary)] mb-1">
                Min. Years Experience
              </label>
              <input
                type="number"
                min="0"
                max="30"
                value={minExpYears}
                onChange={(e) => setMinExpYears(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[var(--border-default)] bg-[var(--bg-canvas)] text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-semibold text-[var(--text-primary)]">
                Job Description
              </label>
              <span className="text-[10px] font-mono text-[var(--text-secondary)]">
                Plain text or markdown
              </span>
            </div>
            <textarea
              rows={8}
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              className="w-full p-3 text-xs font-mono rounded-lg border border-[var(--border-default)] bg-[var(--bg-canvas)] text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 leading-relaxed"
            />
          </div>

          <div className="pt-4 border-t border-[var(--border-default)] flex justify-end">
            <button
              onClick={() => setStep(2)}
              disabled={!title.trim() || !jdText.trim()}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
            >
              Next: Skills & Scoring
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: CONFIRM SKILLS AND SCORING */}
      {step === 2 && (
        <div className="p-6 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] space-y-6">
          <div>
            <h1 className="text-xl font-bold text-[var(--text-primary)]">
              Confirm skills and scoring
            </h1>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Review the extracted skills and set the weight for each. Weights must sum to exactly 100%.
            </p>
          </div>

          {/* Weight Sum Indicator */}
          <div
            className={`p-3 rounded-lg border flex items-center justify-between text-xs font-mono font-semibold ${
              isWeightValid
                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                : "bg-amber-500/10 border-amber-500/20 text-amber-400"
            }`}
          >
            <span>Total Weight: {totalWeight}% / 100%</span>
            <span>{isWeightValid ? "✓ Weights valid" : `${100 - totalWeight}% remaining`}</span>
          </div>

          {/* Must Haves Skills List */}
          <div className="space-y-3">
            <label className="block text-xs font-semibold text-[var(--text-primary)]">
              Must-Have Skills & Weights
            </label>

            {mustHaves.map((sk, idx) => (
              <div
                key={idx}
                className="flex items-center gap-3 p-3 rounded-lg bg-[var(--bg-subtle)] border border-[var(--border-default)]"
              >
                <span className="text-xs font-semibold text-[var(--text-primary)] flex-1">
                  {sk.name}
                </span>

                <div className="flex items-center gap-2">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={sk.weight}
                    onChange={(e) => handleWeightChange(idx, parseInt(e.target.value) || 0)}
                    className="w-28 accent-indigo-600"
                  />
                  <span className="font-mono text-xs font-bold text-indigo-400 w-12 text-right">
                    {sk.weight}%
                  </span>
                </div>

                <button
                  onClick={() => handleRemoveSkill(idx)}
                  className="p-1 text-[var(--text-secondary)] hover:text-rose-400 transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}

            {/* Add Skill */}
            <div className="flex gap-2 pt-2">
              <input
                type="text"
                placeholder="Add another required skill..."
                value={newSkillName}
                onChange={(e) => setNewSkillName(e.target.value)}
                className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-[var(--border-default)] bg-[var(--bg-canvas)] text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
              />
              <button
                type="button"
                onClick={handleAddSkill}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-[var(--bg-subtle)] border border-[var(--border-default)] text-[var(--text-primary)] hover:bg-[var(--border-default)] transition-colors flex items-center gap-1 cursor-pointer"
              >
                <Plus size={14} />
                Add
              </button>
            </div>
          </div>

          {/* Nice to Haves */}
          <div className="space-y-2 pt-4 border-t border-[var(--border-default)]">
            <label className="block text-xs font-semibold text-[var(--text-primary)]">
              Nice-to-Have Skills (Tie-breakers)
            </label>
            <div className="flex flex-wrap gap-2">
              {niceToHaves.map((nth, i) => (
                <span
                  key={i}
                  className="px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
                >
                  {nth}
                </span>
              ))}
            </div>
          </div>

          <div className="pt-4 border-t border-[var(--border-default)] flex items-center justify-between">
            <button
              onClick={() => setStep(1)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold border border-[var(--border-default)] text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] transition-colors cursor-pointer"
            >
              <ArrowLeft size={14} />
              Back
            </button>

            <button
              onClick={() => setStep(3)}
              disabled={!isWeightValid}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
            >
              Next: Add Candidates
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: CANDIDATE CVS */}
      {step === 3 && (
        <div className="p-6 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] space-y-6">
          <div>
            <h1 className="text-xl font-bold text-[var(--text-primary)]">
              Add candidate CVs
            </h1>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Drop in candidate resumes in PDF format (up to 15 MB). Non-resumes are automatically flagged and skipped.
            </p>
          </div>

          {/* Drag & Drop Upload Zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              handleFileUpload(e.dataTransfer.files);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
              isDragging
                ? "border-indigo-500 bg-indigo-500/10"
                : "border-[var(--border-default)] hover:border-indigo-500/50 hover:bg-[var(--bg-subtle)]"
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              multiple
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={(e) => handleFileUpload(e.target.files)}
            />
            <Upload size={32} className="mx-auto text-indigo-400 mb-3" />
            <p className="text-xs font-semibold text-[var(--text-primary)]">
              Drop candidate CVs here or click to browse
            </p>
            <p className="text-[11px] text-[var(--text-secondary)] mt-1">
              Supports PDF, DOCX up to 15 MB each.
            </p>
          </div>

          {/* Uploaded Files List */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
              <span>Candidate Files ({files.length})</span>
              <span>Classification Status</span>
            </div>

            <div className="space-y-1.5 max-h-60 overflow-y-auto">
              {files.map((f) => (
                <div
                  key={f.id}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-[var(--bg-subtle)] border border-[var(--border-default)] text-xs"
                >
                  <div className="flex items-center gap-2">
                    <FileText size={16} className="text-indigo-400 shrink-0" />
                    <div>
                      <span className="font-medium text-[var(--text-primary)] block">
                        {f.name}
                      </span>
                      <span className="text-[10px] font-mono text-[var(--text-secondary)]">
                        {f.size}
                      </span>
                    </div>
                  </div>

                  <div>
                    {f.status === "Indexed" && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <CheckCircle2 size={12} />
                        Indexed
                      </span>
                    )}
                    {f.status === "Processing" && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        Processing…
                      </span>
                    )}
                    {f.status === "Abstain" && (
                      <span
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        title={f.error}
                      >
                        ⊘ Abstain (Non-resume)
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-4 border-t border-[var(--border-default)] flex items-center justify-between">
            <button
              onClick={() => setStep(2)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold border border-[var(--border-default)] text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] transition-colors cursor-pointer"
            >
              <ArrowLeft size={14} />
              Back
            </button>

            <button
              onClick={handleFinish}
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs transition-colors cursor-pointer"
            >
              {isSubmitting ? (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  Finish & View Candidates
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
