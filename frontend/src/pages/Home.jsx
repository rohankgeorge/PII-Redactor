import { useState, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import Header from "@/components/Header";
import UploadZone from "@/components/UploadZone";
import ProcessingState from "@/components/ProcessingState";
import ResultsPanel from "@/components/ResultsPanel";
import ReviewPanel from "@/components/ReviewPanel";
import PrivacyFooter from "@/components/PrivacyFooter";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
const API = `${BACKEND_URL}/api`;

export default function Home() {
  const [state, setState] = useState("idle");
  const [results, setResults] = useState([]);
  const [fileNames, setFileNames] = useState([]);
  const [reviewModeEnabled, setReviewModeEnabled] = useState(false);
  const [reviewState, setReviewState] = useState(null);
  const [policyOptions, setPolicyOptions] = useState({
    redactLocations: true,
    redactCountries: true,
  });

  // Validates supported document types and file size before any upload request is made.
  const validateFiles = useCallback((files) => {
    const valid = Array.from(files).filter((f) => {
      const normalizedName = f.name.toLowerCase();
      return normalizedName.endsWith(".docx") || normalizedName.endsWith(".doc") || normalizedName.endsWith(".pdf");
    });

    if (!valid.length) {
      toast.error("Only .doc, .docx, and text-based .pdf files are supported");
      return [];
    }

    const oversized = valid.filter((f) => f.size > 10 * 1024 * 1024);
    if (oversized.length) {
      toast.error(`${oversized.length} file(s) exceed 10 MB limit`);
      return [];
    }

    return valid;
  }, []);

  // Processes the current files directly through the legacy redact endpoint for one-click output.
  const runInstantRedaction = useCallback(async (validFiles) => {
    setFileNames(validFiles.map((f) => f.name));
    setState("processing");

    const settled = await Promise.allSettled(
      validFiles.map(async (file) => {
        const formData = new FormData();
        formData.append("file", file);
        const { data } = await axios.post(`${API}/redact`, formData);
        return data;
      }),
    );

    const processed = settled.map((entry, index) => ({
      fileName: validFiles[index].name,
      result: entry.status === "fulfilled" ? entry.value : null,
      error: entry.status === "rejected" ? (entry.reason?.response?.data?.detail || "Processing failed") : null,
    }));

    setResults(processed);

    const totalPII = processed.reduce((sum, item) => sum + (item.result?.total || 0), 0);
    const errCount = processed.filter((item) => item.error).length;

    if (errCount === processed.length) {
      setState("error");
      toast.error("All files failed to process");
      return;
    }

    setState("done");
    if (errCount > 0) {
      toast.warning(`${processed.length - errCount}/${processed.length} files processed. ${totalPII} PII items.`);
    } else {
      toast.success(`Redacted ${totalPII} PII item(s) across ${processed.length} file(s)`);
    }
  }, []);

  // Runs the new analyze endpoint so a user can review and deselect redaction candidates before applying.
  const runAnalyzeForReview = useCallback(async (validFiles) => {
    if (validFiles.length > 1) {
      toast.error("Review mode currently supports one file at a time");
      return;
    }

    const file = validFiles[0];
    const formData = new FormData();
    formData.append("file", file);

    setFileNames([file.name]);
    setState("processing");

    try {
      const { data } = await axios.post(`${API}/analyze`, formData);
      const candidateIds = data.candidates?.map((candidate) => candidate.candidate_id) || [];

      setReviewState({
        fileName: file.name,
        analysisId: data.analysis_id,
        candidates: data.candidates || [],
        selectedCandidateIds: candidateIds,
        review: data.review || { review_required: false, manual_review_items: [] },
        stats: data.stats || {},
        total: data.total || 0,
      });
      setState("review");
      toast.success("Analysis complete. Review candidates before applying redaction.");
    } catch (error) {
      setState("error");
      const detail = error?.response?.data?.detail || "Analysis failed";
      toast.error(detail);
    }
  }, []);

  // Entry point from the upload UI that routes the file list into either instant mode or review mode.
  const handleFileSelect = useCallback(async (files) => {
    const validFiles = validateFiles(files);
    if (!validFiles.length) {
      return;
    }

    if (reviewModeEnabled) {
      await runAnalyzeForReview(validFiles);
    } else {
      await runInstantRedaction(validFiles);
    }
  }, [reviewModeEnabled, runAnalyzeForReview, runInstantRedaction, validateFiles]);

  // Persists the user's include/exclude choices by calling apply-redaction and then opens the normal results flow.
  const handleApplyReview = useCallback(async (selectedCandidateIds, selectedPolicyOptions = policyOptions) => {
    if (!reviewState?.analysisId) {
      toast.error("No active analysis found. Please upload again.");
      return;
    }

    const allCandidateIds = reviewState.candidates.map((candidate) => candidate.candidate_id);
    const selectedIds = new Set(selectedCandidateIds);
    const deselectedIds = allCandidateIds.filter((candidateId) => !selectedIds.has(candidateId));

    const payload = {
      analysis_id: reviewState.analysisId,
      redact_locations: selectedPolicyOptions?.redactLocations ?? true,
      redact_countries: selectedPolicyOptions?.redactCountries ?? true,
    };
    if (deselectedIds.length > 0) {
      payload.exclude_candidate_ids = deselectedIds;
    }

    setState("processing");

    try {
      const { data } = await axios.post(`${API}/apply-redaction`, payload);
      setResults([
        {
          fileName: reviewState.fileName,
          result: data,
          error: null,
        },
      ]);
      setState("done");
      toast.success(`Applied redaction with ${selectedCandidateIds.length} selected candidate(s).`);
    } catch (error) {
      setState("review");
      const detail = error?.response?.data?.detail || "Apply redaction failed";
      toast.error(detail);
    }
  }, [policyOptions, reviewState]);

  /* ── Direct-URL downloads via native browser navigation ── */
  const handleDownload = useCallback(
    (index) => {
      const r = results[index];
      if (r?.result?.file_id) {
        // Using an iframe to trigger download avoids popup blockers
        // and doesn't navigate away from the current page
        const iframe = document.createElement("iframe");
        iframe.style.display = "none";
        iframe.src = `${API}/download/${r.result.file_id}`;
        document.body.appendChild(iframe);
        setTimeout(() => document.body.removeChild(iframe), 10000);
      }
    },
    [results],
  );

  const handleDownloadAll = useCallback(() => {
    results.forEach((r, i) => {
      if (r?.result?.file_id) {
        setTimeout(() => {
          const iframe = document.createElement("iframe");
          iframe.style.display = "none";
          iframe.src = `${API}/download/${r.result.file_id}`;
          document.body.appendChild(iframe);
          setTimeout(() => document.body.removeChild(iframe), 10000);
        }, i * 500);
      }
    });
  }, [results]);

  const handleExportAudit = useCallback(() => {
    const fileIds = results.filter((r) => r.result?.file_id).map((r) => r.result.file_id);
    if (fileIds.length === 1) {
      const iframe = document.createElement("iframe");
      iframe.style.display = "none";
      iframe.src = `${API}/audit-csv/${fileIds[0]}`;
      document.body.appendChild(iframe);
      setTimeout(() => document.body.removeChild(iframe), 10000);
    } else if (fileIds.length > 1) {
      // POST batch audit request via form
      const form = document.createElement("form");
      form.method = "POST";
      form.action = `${API}/audit-csv-batch`;
      form.style.display = "none";
      fileIds.forEach((id) => {
        const input = document.createElement("input");
        input.name = "file_ids";
        input.value = id;
        form.appendChild(input);
      });
      document.body.appendChild(form);
      form.submit();
      setTimeout(() => document.body.removeChild(form), 1000);
    }
  }, [results]);

  // Returns the view back to initial upload state and clears processing/review artifacts.
  const handleReset = useCallback(() => {
    setState("idle");
    setResults([]);
    setFileNames([]);
    setReviewState(null);
    setPolicyOptions({
      redactLocations: true,
      redactCountries: true,
    });
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {state === "idle" && (
          <div className="space-y-8">
            <div className="mx-auto max-w-xl rounded-xl border border-border bg-card/40 p-4 sm:p-5">
              <div className="flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <Label htmlFor="review-mode-toggle" className="text-sm font-semibold text-foreground">Review mode</Label>
                  <p className="text-xs text-muted-foreground">
                    Analyze first, choose candidates, then apply redaction.
                  </p>
                </div>
                <Switch
                  id="review-mode-toggle"
                  checked={reviewModeEnabled}
                  onCheckedChange={setReviewModeEnabled}
                  data-testid="review-mode-toggle"
                />
              </div>
            </div>
            <UploadZone onFileSelect={handleFileSelect} allowMultiple={!reviewModeEnabled} />
          </div>
        )}
        {state === "processing" && <ProcessingState fileNames={fileNames} />}
        {state === "review" && reviewState && (
          <ReviewPanel
            fileName={reviewState.fileName}
            candidates={reviewState.candidates}
            selectedCandidateIds={reviewState.selectedCandidateIds}
            reviewPayload={reviewState.review}
            policyOptions={policyOptions}
            onPolicyChange={setPolicyOptions}
            onSelectionChange={(nextSelection) => {
              setReviewState((current) => ({
                ...current,
                selectedCandidateIds: nextSelection,
              }));
            }}
            onApply={handleApplyReview}
            onReset={handleReset}
          />
        )}
        {(state === "done" || state === "error") && (
          <ResultsPanel
            results={results}
            onDownload={handleDownload}
            onDownloadAll={handleDownloadAll}
            onExportAudit={handleExportAudit}
            onReset={handleReset}
            hasError={state === "error"}
          />
        )}
      </main>
      <PrivacyFooter />
    </div>
  );
}
