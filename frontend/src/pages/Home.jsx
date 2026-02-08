import { useState, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import Header from "@/components/Header";
import UploadZone from "@/components/UploadZone";
import ProcessingState from "@/components/ProcessingState";
import ResultsPanel from "@/components/ResultsPanel";
import PrivacyFooter from "@/components/PrivacyFooter";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function downloadBlob(base64Data, filename, mimeType = "application/vnd.openxmlformats-officedocument.wordprocessingml.document") {
  try {
    const bytes = atob(base64Data);
    const arr = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
    const blob = new Blob([arr], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    }, 250);
  } catch {
    toast.error("Download failed");
  }
}

export default function Home() {
  const [state, setState] = useState("idle");
  const [results, setResults] = useState([]);
  const [fileNames, setFileNames] = useState([]);

  const handleFileSelect = useCallback(async (files) => {
    const valid = Array.from(files).filter((f) => {
      const n = f.name.toLowerCase();
      return n.endsWith(".docx") || n.endsWith(".doc");
    });
    if (!valid.length) {
      toast.error("Only .doc and .docx files are supported");
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

  const handleDownload = useCallback(
    (index) => {
      const r = results[index];
      if (r?.result?.file_base64) downloadBlob(r.result.file_base64, r.result.filename);
    },
    [results],
  );

  const handleDownloadAll = useCallback(() => {
    results.forEach((r, i) => {
      if (r?.result?.file_base64) setTimeout(() => downloadBlob(r.result.file_base64, r.result.filename), i * 300);
    });
  }, [results]);

  const handleExportAudit = useCallback(() => {
    let csv = "Document,Category,Placeholder,Location\n";
    results.forEach((r) => {
      (r.result?.audit_log || []).forEach((e) => {
        csv += `"${r.fileName}","${e.category}","${e.placeholder}","${e.location}"\n`;
      });
    });
    csv += "\n\nSummary\nDocument,Total PII,Status\n";
    results.forEach((r) => {
      csv += `"${r.fileName}",${r.result?.total || 0},"${r.error || "Success"}"\n`;
    });
    // Category breakdown
    csv += "\n\nCategory Breakdown\nDocument,Category,Count\n";
    results.forEach((r) => {
      Object.entries(r.result?.stats || {}).forEach(([cat, count]) => {
        csv += `"${r.fileName}","${cat}",${count}\n`;
      });
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = url;
    a.download = `pii_audit_report_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    }, 250);
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
