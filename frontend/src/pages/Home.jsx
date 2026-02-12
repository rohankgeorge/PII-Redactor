import { useState, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import Header from "@/components/Header";
import UploadZone from "@/components/UploadZone";
import ProcessingState from "@/components/ProcessingState";
import ResultsPanel from "@/components/ResultsPanel";
import PrivacyFooter from "@/components/PrivacyFooter";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
const API = `${BACKEND_URL}/api`;

export default function Home() {
  const [state, setState] = useState("idle");
  const [results, setResults] = useState([]);
  const [fileNames, setFileNames] = useState([]);

  const handleFileSelect = useCallback(async (files) => {
    const valid = Array.from(files).filter((f) => {
      const n = f.name.toLowerCase();
      return n.endsWith(".docx") || n.endsWith(".doc") || n.endsWith(".pdf");
    });
    if (!valid.length) {
      toast.error("Only .doc, .docx, and text-based .pdf files are supported");
      return;
    }
    const oversized = valid.filter((f) => f.size > 10 * 1024 * 1024);
    if (oversized.length) {
      toast.error(`${oversized.length} file(s) exceed 10 MB limit`);
      return;
    }

    setFileNames(valid.map((f) => f.name));
    setState("processing");

    const settled = await Promise.allSettled(
      valid.map(async (file) => {
        const fd = new FormData();
        fd.append("file", file);
        const { data } = await axios.post(`${API}/redact`, fd);
        return data;
      }),
    );

    const processed = settled.map((s, i) => ({
      fileName: valid[i].name,
      result: s.status === "fulfilled" ? s.value : null,
      error: s.status === "rejected" ? (s.reason?.response?.data?.detail || "Processing failed") : null,
    }));

    setResults(processed);

    const totalPII = processed.reduce((s, r) => s + (r.result?.total || 0), 0);
    const errCount = processed.filter((r) => r.error).length;

    if (errCount === processed.length) {
      setState("error");
      toast.error("All files failed to process");
    } else {
      setState("done");
      if (errCount > 0) toast.warning(`${processed.length - errCount}/${processed.length} files processed. ${totalPII} PII items.`);
      else toast.success(`Redacted ${totalPII} PII item(s) across ${processed.length} file(s)`);
    }
  }, []);

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

  const handleReset = useCallback(() => {
    setState("idle");
    setResults([]);
    setFileNames([]);
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {state === "idle" && <UploadZone onFileSelect={handleFileSelect} />}
        {state === "processing" && <ProcessingState fileNames={fileNames} />}
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
