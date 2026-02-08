import { useState, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import Header from "@/components/Header";
import UploadZone from "@/components/UploadZone";
import ProcessingState from "@/components/ProcessingState";
import ResultsPanel from "@/components/ResultsPanel";
import PrivacyFooter from "@/components/PrivacyFooter";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Home() {
  const [state, setState] = useState("idle");
  const [result, setResult] = useState(null);
  const [fileName, setFileName] = useState("");

  const handleFileSelect = useCallback(async (file) => {
    if (!file.name.toLowerCase().endsWith(".docx")) {
      toast.error("Only .docx files are supported");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error("File too large. Maximum size is 10 MB.");
      return;
    }

    setFileName(file.name);
    setState("processing");

    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await axios.post(`${API}/redact`, formData);
      setResult(data);
      setState("done");
      toast.success(`Redacted ${data.total} PII items`);
    } catch (err) {
      setState("error");
      toast.error(err.response?.data?.detail || "Failed to process document");
    }
  }, []);

  const handleDownload = useCallback(() => {
    if (!result) return;
    const bytes = atob(result.file_base64);
    const arr = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
    const blob = new Blob([arr], {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = result.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [result]);

  const handleReset = useCallback(() => {
    setState("idle");
    setResult(null);
    setFileName("");
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {state === "idle" && <UploadZone onFileSelect={handleFileSelect} />}
        {state === "processing" && <ProcessingState fileName={fileName} />}
        {(state === "done" || state === "error") && (
          <ResultsPanel
            result={result}
            onDownload={handleDownload}
            onReset={handleReset}
            hasError={state === "error"}
          />
        )}
      </main>
      <PrivacyFooter />
    </div>
  );
}
