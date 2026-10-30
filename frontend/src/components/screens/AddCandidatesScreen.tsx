import React, { useState, useRef } from "react";
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";
import type { JobItem } from "../../lib/mockData";

interface AddCandidatesScreenProps {
  job: JobItem;
  onNavigate: (path: string) => void;
  onUploadSuccess?: () => void;
}

interface CVFileItem {
  id: string;
  name: string;
  size: string;
  hash: string;
  status: "Queued" | "Parsing" | "Indexing" | "Completed" | "Abstained" | "Duplicate";
  error?: string;
}

export const AddCandidatesScreen: React.FC<AddCandidatesScreenProps> = ({
  job,
  onNavigate,
  onUploadSuccess,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Existing CV hashes in system to demonstrate duplicate detection
  const KNOWN_HASHES = new Set(["hash-alex-rivera-6299", "hash-elena-rostova-8412"]);

  const [files, setFiles] = useState<CVFileItem[]>([
    {
      id: "cv-1",
      name: "elena_rostova_resume.pdf",
      size: "280 KB",
      hash: "hash-elena-rostova-8412",
      status: "Duplicate",
      error: "Duplicate CV hash detected: already indexed in REQ-204 candidate pool.",
    },
    {
      id: "cv-2",
      name: "q3_cloud_infrastructure_invoice.pdf",
      size: "340 KB",
      hash: "hash-invoice-9921",
      status: "Abstained",
      error: "Non-resume document flagged by intake classifier (confidence: 99.2% non-resume).",
    },
    {
      id: "cv-3",
      name: "david_kim_distributed_systems_cv.pdf",
      size: "210 KB",
      hash: "hash-david-kim-3382",
      status: "Completed",
    },
  ]);

  const handleDrop = (incoming: FileList | null) => {
    if (!incoming || incoming.length === 0) return;

    const newItems: CVFileItem[] = [];
    Array.from(incoming).forEach((f, idx) => {
      const lower = f.name.toLowerCase();
      const isInvoice = lower.includes("invoice") || lower.includes("receipt") || lower.includes("billing");
      const isDuplicate = KNOWN_HASHES.has(f.name);

      let status: CVFileItem["status"] = "Completed";
      let error: string | undefined = undefined;

      if (isDuplicate) {
        status = "Duplicate";
        error = "Duplicate CV hash detected in active database.";
      } else if (isInvoice) {
        status = "Abstained";
        error = "Non-resume detected by intake classifier. Document will not be ranked.";
      }

      newItems.push({
        id: `cv-new-${Date.now()}-${idx}`,
        name: f.name,
        size: `${Math.round(f.size / 1024)} KB`,
        hash: `hash-${f.name}-${Date.now()}`,
        status,
        error,
      });
    });

    setFiles((prev) => [...newItems, ...prev]);
  };

  const completedCount = files.filter((f) => f.status === "Completed").length;
  const duplicateCount = files.filter((f) => f.status === "Duplicate").length;
  const abstainCount = files.filter((f) => f.status === "Abstained").length;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => onNavigate(`/jobs/${job.id}/candidates`)}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors mb-2 cursor-pointer"
          >
            <ArrowLeft size={14} />
            Back to Ranked Candidates
          </button>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            Add Candidates to Requisition
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1 font-mono">
            {job.id.toUpperCase().replace("JOB-", "REQ-")} · {job.title}
          </p>
        </div>

        <button
          onClick={() => {
            if (onUploadSuccess) onUploadSuccess();
            onNavigate(`/jobs/${job.id}/candidates`);
          }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs transition-colors cursor-pointer"
        >
          View Ranked Candidates
          <ArrowRight size={14} />
        </button>
      </div>

      {/* Upload Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          handleDrop(e.dataTransfer.files);
        }}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
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
          onChange={(e) => handleDrop(e.target.files)}
        />
        <Upload size={36} className="mx-auto text-indigo-400 mb-3" />
        <p className="text-sm font-semibold text-[var(--text-primary)]">
          Drop candidate resumes here or click to browse
        </p>
        <p className="text-xs text-[var(--text-secondary)] mt-1">
          Supports PDF, DOCX, and TXT files up to 15 MB each.
        </p>
        <div className="mt-4 flex flex-wrap items-center justify-center gap-4 text-[11px] font-mono text-[var(--text-secondary)]">
          <span>✓ Automated Resume Gate</span>
          <span>✓ Duplicate Hash Detection</span>
          <span>✓ Multi-chunk Semantic Indexing</span>
        </div>
      </div>

      {/* Summary Pills */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-emerald-400 text-xs font-mono">
          <span className="block text-[10px] uppercase font-bold">Successfully Indexed</span>
          <span className="text-lg font-bold">{completedCount} Resumes</span>
        </div>
        <div className="p-3 rounded-lg border border-amber-500/20 bg-amber-500/10 text-amber-400 text-xs font-mono">
          <span className="block text-[10px] uppercase font-bold">Duplicate Detected</span>
          <span className="text-lg font-bold">{duplicateCount} Skipped</span>
        </div>
        <div className="p-3 rounded-lg border border-rose-500/20 bg-rose-500/10 text-rose-400 text-xs font-mono">
          <span className="block text-[10px] uppercase font-bold">Abstained (Non-Resume)</span>
          <span className="text-lg font-bold">{abstainCount} Flagged</span>
        </div>
      </div>

      {/* File Classification Table */}
      <div className="p-6 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] space-y-4">
        <h2 className="text-sm font-bold text-[var(--text-primary)]">
          Batch Intake Processing Queue
        </h2>

        <div className="space-y-2">
          {files.map((file) => (
            <div
              key={file.id}
              className="p-3 rounded-lg bg-[var(--bg-subtle)] border border-[var(--border-default)] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
            >
              <div className="flex items-start gap-2.5 min-w-0">
                <FileText size={18} className="text-indigo-400 shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <span className="font-semibold text-[var(--text-primary)] block truncate">
                    {file.name}
                  </span>
                  <div className="flex items-center gap-2 text-[10px] font-mono text-[var(--text-secondary)]">
                    <span>{file.size}</span>
                    <span>·</span>
                    <span className="truncate">{file.hash}</span>
                  </div>
                  {file.error && (
                    <p className="text-[11px] text-rose-400 mt-1 flex items-center gap-1">
                      <AlertTriangle size={12} className="shrink-0" />
                      <span>{file.error}</span>
                    </p>
                  )}
                </div>
              </div>

              <div className="shrink-0">
                {file.status === "Completed" && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <CheckCircle2 size={13} />
                    Indexed & Scored
                  </span>
                )}
                {file.status === "Duplicate" && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    <AlertTriangle size={13} />
                    Duplicate Hash
                  </span>
                )}
                {file.status === "Abstained" && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-mono font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    <ShieldAlert size={13} />
                    Abstain (Non-Resume)
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
