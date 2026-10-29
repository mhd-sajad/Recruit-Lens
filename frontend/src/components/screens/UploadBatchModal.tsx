import React, { useState, useRef } from "react";
import { Modal } from "../common/Modal";
import { api } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import {
  UploadCloud,
  FileText,
  AlertCircle,
  Trash2,
  Loader2,
} from "lucide-react";

interface UploadBatchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onBatchCompleted: () => void;
}

export const UploadBatchModal: React.FC<UploadBatchModalProps> = ({
  isOpen,
  onClose,
  onBatchCompleted,
}) => {
  const { activeJob } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progressStatus, setProgressStatus] = useState<string | null>(null);
  const [progressPercent, setProgressPercent] = useState<number>(0);

  const handleFilesSelected = (files: FileList | null) => {
    if (!files) return;
    setValidationError(null);

    const newFiles: File[] = [];
    const maxFiles = 200;

    if (selectedFiles.length + files.length > maxFiles) {
      setValidationError(`Maximum batch limit is 200 resumes. Selected batch exceeds limit.`);
      return;
    }

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (!file) continue;
      // Max file size 15 MB
      if (file.size > 15 * 1024 * 1024) {
        setValidationError(`File "${file.name}" exceeds 15 MB maximum size.`);
        return;
      }
      newFiles.push(file);
    }

    setSelectedFiles((prev) => [...prev, ...newFiles]);
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleStartUpload = async () => {
    if (!activeJob) {
      setValidationError("Please select or create an active Job Requisition first.");
      return;
    }
    if (selectedFiles.length === 0) {
      setValidationError("Please select at least one resume file.");
      return;
    }

    setValidationError(null);
    setUploading(true);
    setProgressPercent(10);
    setProgressStatus("Validating and uploading files...");

    try {
      const uploadRes = await api.uploadResumes(activeJob.id, selectedFiles);
      setProgressPercent(40);
      setProgressStatus(`Files uploaded. Starting screening pipeline...`);

      const taskId = uploadRes.id || uploadRes.task_id;
      // Poll task if taskId returned
      if (taskId) {
        let done = false;
        let attempts = 0;
        while (!done && attempts < 60) {
          attempts++;
          await new Promise((r) => setTimeout(r, 1000));
          const task = await api.getTaskStatus(taskId);
          if (task.status === "completed") {
            done = true;
            setProgressPercent(100);
            setProgressStatus("Screening pipeline completed successfully!");
          } else if (task.status === "failed") {
            throw new Error(task.error || "Batch screening pipeline failed");
          } else {
            setProgressPercent(Math.min(95, 40 + attempts * 3));
            setProgressStatus(
              task.current_step
                ? `Pipeline processing: ${task.current_step}`
                : `Screening candidates... (${task.progress_percent || attempts * 2}%)`
            );
          }
        }
      } else {
        setProgressPercent(100);
        setProgressStatus("Processing complete!");
      }

      await new Promise((r) => setTimeout(r, 600));
      onBatchCompleted();
      onClose();
      setSelectedFiles([]);
      setUploading(false);
      setProgressStatus(null);
    } catch (err: unknown) {
      setUploading(false);
      if (err instanceof Error) {
        setValidationError(err.message || "Upload or screening failed.");
      } else {
        setValidationError("Upload or screening failed.");
      }
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        if (!uploading) onClose();
      }}
      title="Bulk Resume Upload & Screening"
      description={`Upload candidate resumes for active job: "${activeJob?.title || "None Selected"}"`}
      maxWidth="xl"
      footer={
        <div className="flex items-center justify-between w-full">
          <span className="text-xs text-slate-400">
            {selectedFiles.length} file{selectedFiles.length === 1 ? "" : "s"} selected
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={uploading}
              onClick={onClose}
              className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={uploading || selectedFiles.length === 0}
              onClick={handleStartUpload}
              className="px-4 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg shadow-sm transition flex items-center gap-1.5"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <UploadCloud className="w-3.5 h-3.5" />
                  <span>Run Screening Pipeline</span>
                </>
              )}
            </button>
          </div>
        </div>
      }
    >
      <div className="space-y-4">
        {validationError && (
          <div
            role="alert"
            aria-live="assertive"
            className="p-3 bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 rounded-lg text-xs flex items-center gap-2"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{validationError}</span>
          </div>
        )}

        {/* Dropzone */}
        {!uploading && (
          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              handleFilesSelected(e.dataTransfer.files);
            }}
            className="border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-blue-500 dark:hover:border-blue-400 rounded-xl p-8 text-center cursor-pointer transition bg-slate-50/50 dark:bg-slate-800/30 space-y-2"
          >
            <div className="w-10 h-10 rounded-full bg-blue-50 dark:bg-blue-950/80 text-blue-600 dark:text-blue-400 flex items-center justify-center mx-auto">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                Click to browse or drop resumes here
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                PDF, DOCX, TXT format • Max 15MB per file • Up to 200 resumes per batch
              </p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={(e) => handleFilesSelected(e.target.files)}
            />
          </div>
        )}

        {/* Upload Progress Status */}
        {uploading && (
          <div className="p-6 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200 dark:border-slate-700 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                {progressStatus || "Screening batch..."}
              </span>
              <span className="font-mono text-slate-500">{progressPercent}%</span>
            </div>
            <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <div className="grid grid-cols-4 gap-2 pt-2 text-[11px] text-center text-slate-400">
              <span className={progressPercent >= 25 ? "text-emerald-600 font-semibold" : ""}>
                1. Text Parsing
              </span>
              <span className={progressPercent >= 50 ? "text-emerald-600 font-semibold" : ""}>
                2. Chunk Embed
              </span>
              <span className={progressPercent >= 75 ? "text-emerald-600 font-semibold" : ""}>
                3. Evidence RAG
              </span>
              <span className={progressPercent >= 95 ? "text-emerald-600 font-semibold" : ""}>
                4. Fit Scoring
              </span>
            </div>
          </div>
        )}

        {/* Selected files list */}
        {selectedFiles.length > 0 && !uploading && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
              <span>Selected Resumes ({selectedFiles.length})</span>
              <button
                type="button"
                onClick={() => setSelectedFiles([])}
                className="text-[11px] text-rose-600 hover:underline"
              >
                Clear all
              </button>
            </div>
            <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
              {selectedFiles.map((file, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText className="w-4 h-4 text-blue-500 shrink-0" />
                    <span className="truncate text-slate-800 dark:text-slate-200">
                      {file.name}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      ({(file.size / 1024).toFixed(0)} KB)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveFile(idx)}
                    className="text-slate-400 hover:text-rose-600 p-1 rounded"
                    aria-label={`Remove ${file.name}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};
