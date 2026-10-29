import React, { useState } from "react";
import { Modal } from "../common/Modal";
import { api } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { AlertCircle, Plus, Trash2, CheckCircle2 } from "lucide-react";

interface JobCreateConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const JobCreateConfirmModal: React.FC<JobCreateConfirmModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { refreshJobs, setActiveJob } = useAuth();
  const [step, setStep] = useState<1 | 2>(1);
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("Engineering");
  const [location, setLocation] = useState("Remote");
  const [description, setDescription] = useState("");
  const [minYears, setMinYears] = useState(3);
  const [minDegree, setMinDegree] = useState("bachelor");

  const [mustHaveSkills, setMustHaveSkills] = useState<string[]>([
    "Python",
    "PostgreSQL",
    "FastAPI",
  ]);
  const [niceToHaveSkills, setNiceToHaveSkills] = useState<string[]>([
    "Docker",
    "TypeScript",
    "Redis",
  ]);
  const [newMustHave, setNewMustHave] = useState("");
  const [newNiceToHave, setNewNiceToHave] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleNext = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Job Title is required.");
      return;
    }
    setError(null);
    setStep(2);
  };

  const handleAddMustHave = () => {
    if (newMustHave.trim() && !mustHaveSkills.includes(newMustHave.trim())) {
      setMustHaveSkills([...mustHaveSkills, newMustHave.trim()]);
      setNewMustHave("");
    }
  };

  const handleRemoveMustHave = (skill: string) => {
    setMustHaveSkills(mustHaveSkills.filter((s) => s !== skill));
  };

  const handleAddNiceToHave = () => {
    if (newNiceToHave.trim() && !niceToHaveSkills.includes(newNiceToHave.trim())) {
      setNiceToHaveSkills([...niceToHaveSkills, newNiceToHave.trim()]);
      setNewNiceToHave("");
    }
  };

  const handleRemoveNiceToHave = (skill: string) => {
    setNiceToHaveSkills(niceToHaveSkills.filter((s) => s !== skill));
  };

  const handleSubmit = async () => {
    setError(null);
    setLoading(true);
    try {
      const created = await api.createJob({
        title: title.trim(),
        department: department.trim(),
        location: location.trim(),
        raw_text: description.trim() || title.trim(),
        description: description.trim() || title.trim(),
        min_years_experience: Number(minYears),
        min_degree: minDegree,
        required_skills: mustHaveSkills,
        nice_to_have_skills: niceToHaveSkills,
      });

      await refreshJobs();
      setActiveJob(created);
      onClose();
      // Reset form
      setStep(1);
      setTitle("");
      setDescription("");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || "Failed to create job requisition.");
      } else {
        setError("Failed to create job requisition.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={step === 1 ? "Step 1: Create Job Requisition" : "Step 2: Confirm Extracted Requirements"}
      description={
        step === 1
          ? "Paste job description text or configure requisition details"
          : "Review and approve extracted must-haves, nice-to-haves, and qualifications"
      }
      maxWidth="xl"
      footer={
        <div className="flex items-center justify-between w-full">
          {step === 2 ? (
            <button
              type="button"
              onClick={() => setStep(1)}
              className="px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
            >
              ← Back to Details
            </button>
          ) : (
            <div />
          )}

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition"
            >
              Cancel
            </button>
            {step === 1 ? (
              <button
                type="button"
                onClick={handleNext}
                className="px-4 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition"
              >
                Next: Review Requirements →
              </button>
            ) : (
              <button
                type="button"
                disabled={loading}
                onClick={handleSubmit}
                className="px-4 py-1.5 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg shadow-sm transition flex items-center gap-1.5"
              >
                {loading ? (
                  <span>Saving Requisition...</span>
                ) : (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Confirm & Activate Requisition</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      }
    >
      {error && (
        <div
          role="alert"
          aria-live="assertive"
          className="p-3 bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 rounded-lg text-xs flex items-center gap-2"
        >
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {step === 1 ? (
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label
              htmlFor="job-title-field"
              className="text-xs font-medium text-slate-700 dark:text-slate-300"
            >
              Job Title <span className="text-rose-500">*</span>
            </label>
            <input
              id="job-title-field"
              type="text"
              required
              placeholder="e.g. Senior Machine Learning Engineer"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full text-xs px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label
                htmlFor="job-dept-field"
                className="text-xs font-medium text-slate-700 dark:text-slate-300"
              >
                Department
              </label>
              <input
                id="job-dept-field"
                type="text"
                placeholder="e.g. AI / Core Infrastructure"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="w-full text-xs px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              />
            </div>
            <div className="space-y-1.5">
              <label
                htmlFor="job-loc-field"
                className="text-xs font-medium text-slate-700 dark:text-slate-300"
              >
                Location
              </label>
              <input
                id="job-loc-field"
                type="text"
                placeholder="e.g. Remote (US / EMEA)"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full text-xs px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="job-desc-field"
              className="text-xs font-medium text-slate-700 dark:text-slate-300"
            >
              Job Description & Raw Text
            </label>
            <textarea
              id="job-desc-field"
              rows={5}
              placeholder="Paste full job description text or hiring rubric here..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full text-xs px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 font-mono"
            />
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label
                htmlFor="job-min-years-field"
                className="text-xs font-medium text-slate-700 dark:text-slate-300"
              >
                Minimum Years Experience
              </label>
              <input
                id="job-min-years-field"
                type="number"
                min="0"
                max="30"
                value={minYears}
                onChange={(e) => setMinYears(Number(e.target.value))}
                className="w-full text-xs px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              />
            </div>
            <div className="space-y-1.5">
              <label
                htmlFor="job-min-degree-field"
                className="text-xs font-medium text-slate-700 dark:text-slate-300"
              >
                Minimum Degree Requirement
              </label>
              <select
                id="job-min-degree-field"
                value={minDegree}
                onChange={(e) => setMinDegree(e.target.value)}
                className="w-full text-xs px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              >
                <option value="none">No Degree Required</option>
                <option value="associate">Associate's Degree</option>
                <option value="bachelor">Bachelor's Degree</option>
                <option value="master">Master's Degree</option>
                <option value="doctorate">Doctorate / Ph.D.</option>
              </select>
            </div>
          </div>

          {/* Must-have skills */}
          <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-800">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                Must-Have Skills (Strict Gate)
              </span>
              <span className="text-[11px] text-slate-400">
                Missing any prevents FastTrack tier
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {mustHaveSkills.map((s) => (
                <span
                  key={s}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-300 text-xs font-mono"
                >
                  {s}
                  <button
                    type="button"
                    onClick={() => handleRemoveMustHave(s)}
                    className="hover:text-rose-600"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Add must-have skill..."
                value={newMustHave}
                onChange={(e) => setNewMustHave(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddMustHave();
                  }
                }}
                className="flex-1 text-xs px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg"
              />
              <button
                type="button"
                onClick={handleAddMustHave}
                className="px-3 py-1.5 text-xs bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg flex items-center gap-1"
              >
                <Plus className="w-3 h-3" /> Add
              </button>
            </div>
          </div>

          {/* Nice-to-have skills */}
          <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-800">
            <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">
              Nice-to-Have Skills (Bonus Weight)
            </span>
            <div className="flex flex-wrap gap-1.5">
              {niceToHaveSkills.map((s) => (
                <span
                  key={s}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-blue-50 dark:bg-blue-950/60 border border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-300 text-xs font-mono"
                >
                  {s}
                  <button
                    type="button"
                    onClick={() => handleRemoveNiceToHave(s)}
                    className="hover:text-rose-600"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Add nice-to-have skill..."
                value={newNiceToHave}
                onChange={(e) => setNewNiceToHave(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddNiceToHave();
                  }
                }}
                className="flex-1 text-xs px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg"
              />
              <button
                type="button"
                onClick={handleAddNiceToHave}
                className="px-3 py-1.5 text-xs bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg flex items-center gap-1"
              >
                <Plus className="w-3 h-3" /> Add
              </button>
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
};
