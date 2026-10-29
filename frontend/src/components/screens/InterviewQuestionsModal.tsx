import React, { useState } from "react";
import { Modal } from "../common/Modal";
import { Trash2, Edit3, Plus, CheckCircle2, FileText } from "lucide-react";

export interface InterviewQuestionItem {
  id: string;
  question: string;
  topic?: string;
  evidence_rationale?: string;
  probe_criteria?: string;
}

interface InterviewQuestionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidateName: string;
  initialQuestions?: InterviewQuestionItem[];
}

export const InterviewQuestionsModal: React.FC<InterviewQuestionsModalProps> = ({
  isOpen,
  onClose,
  candidateName,
  initialQuestions,
}) => {
  const [questions, setQuestions] = useState<InterviewQuestionItem[]>(
    initialQuestions && initialQuestions.length > 0
      ? initialQuestions
      : [
          {
            id: "q-1",
            question:
              "Can you elaborate on your experience designing and maintaining high-throughput FastAPI microservices?",
            topic: "Architecture & Concurrency",
            evidence_rationale: "Resume highlights backend API work with FastAPI and PostgreSQL.",
            probe_criteria: "Look for knowledge of async event loop, connection pooling, and latency profiling.",
          },
          {
            id: "q-2",
            question:
              "Describe a scenario where you resolved schema drift or query bottlenecks in PostgreSQL.",
            topic: "Database Reliability",
            evidence_rationale: "Candidate lists PostgreSQL and relational databases as core competencies.",
            probe_criteria: "Verify familiarity with EXPLAIN ANALYZE, index selection, and isolation levels.",
          },
          {
            id: "q-3",
            question:
              "How do you approach automated testing and continuous integration across distributed systems?",
            topic: "Testing & CI/CD",
            evidence_rationale: "Mention of Docker and CI/CD pipelines in resume experience.",
            probe_criteria: "Assess commitment to regression testing, mock strategies, and coverage gates.",
          },
        ]
  );

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [newQuestionText, setNewQuestionText] = useState("");
  const [newTopic, setNewTopic] = useState("");

  const handleStartEdit = (q: InterviewQuestionItem) => {
    setEditingId(q.id);
    setEditText(q.question);
  };

  const handleSaveEdit = (id: string) => {
    setQuestions(
      questions.map((q) => (q.id === id ? { ...q, question: editText } : q))
    );
    setEditingId(null);
  };

  const handleRemove = (id: string) => {
    setQuestions(questions.filter((q) => q.id !== id));
  };

  const handleAddQuestion = () => {
    if (!newQuestionText.trim()) return;
    const newQ: InterviewQuestionItem = {
      id: `q-${Date.now()}`,
      question: newQuestionText.trim(),
      topic: newTopic.trim() || "Technical Domain",
      evidence_rationale: "Added by recruiter for candidate interview.",
      probe_criteria: "Custom interview evaluation criteria.",
    };
    setQuestions([...questions, newQ]);
    setNewQuestionText("");
    setNewTopic("");
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Tailored Interview Questions"
      description={`Grounded question rubric with cited evidence rationale for: ${candidateName}`}
      maxWidth="2xl"
      footer={
        <div className="flex items-center justify-between w-full">
          <span className="text-xs text-slate-400">
            {questions.length} questions prepared
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition"
          >
            Done
          </button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* List of questions */}
        <div className="space-y-3">
          {questions.map((q, idx) => (
            <div
              key={q.id}
              className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 space-y-2.5"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-blue-600 dark:text-blue-400 font-mono">
                  Question #{idx + 1} • {q.topic || "Core Competency"}
                </span>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleStartEdit(q)}
                    className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded"
                    aria-label="Edit question"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleRemove(q.id)}
                    className="p-1 text-slate-400 hover:text-rose-600 rounded"
                    aria-label="Remove question"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {editingId === q.id ? (
                <div className="space-y-2">
                  <textarea
                    rows={2}
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="w-full text-xs p-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg"
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => setEditingId(null)}
                      className="px-2.5 py-1 text-xs text-slate-500"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handleSaveEdit(q.id)}
                      className="px-3 py-1 text-xs font-semibold text-white bg-blue-600 rounded-lg"
                    >
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <p className="text-xs font-medium text-slate-800 dark:text-slate-200 leading-relaxed">
                  {q.question}
                </p>
              )}

              {/* Rationale & Probe criteria */}
              <div className="pt-2 border-t border-slate-200/80 dark:border-slate-700/60 grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                <div className="text-slate-500 dark:text-slate-400 flex items-start gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-blue-500 shrink-0 mt-0.5" />
                  <span>
                    <strong className="text-slate-700 dark:text-slate-300">Rationale:</strong>{" "}
                    {q.evidence_rationale}
                  </span>
                </div>
                <div className="text-slate-500 dark:text-slate-400 flex items-start gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                  <span>
                    <strong className="text-slate-700 dark:text-slate-300">Probe Criteria:</strong>{" "}
                    {q.probe_criteria}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Add custom question */}
        <div className="p-3 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 space-y-2">
          <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
            Add Custom Question
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <input
              type="text"
              placeholder="Topic / Category"
              value={newTopic}
              onChange={(e) => setNewTopic(e.target.value)}
              className="text-xs px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg sm:col-span-1"
            />
            <input
              type="text"
              placeholder="Question text..."
              value={newQuestionText}
              onChange={(e) => setNewQuestionText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleAddQuestion();
              }}
              className="text-xs px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg sm:col-span-2"
            />
          </div>
          <button
            onClick={handleAddQuestion}
            disabled={!newQuestionText.trim()}
            className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/60 rounded-lg transition disabled:opacity-40"
          >
            <Plus className="w-3.5 h-3.5" /> Add to Rubric
          </button>
        </div>
      </div>
    </Modal>
  );
};
