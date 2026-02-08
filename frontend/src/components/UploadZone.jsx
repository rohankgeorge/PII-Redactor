import { useCallback, useState, useRef } from "react";
import { Upload, FileText } from "lucide-react";

export default function UploadZone({ onFileSelect }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const prevent = useCallback((e) => { e.preventDefault(); e.stopPropagation(); }, []);

  const onDragEnter = useCallback((e) => { prevent(e); setDragging(true); }, [prevent]);
  const onDragLeave = useCallback((e) => { prevent(e); setDragging(false); }, [prevent]);
  const onDrop = useCallback(
    (e) => { prevent(e); setDragging(false); if (e.dataTransfer.files?.[0]) onFileSelect(e.dataTransfer.files[0]); },
    [prevent, onFileSelect],
  );

  return (
    <div className="flex flex-col items-center justify-center min-h-[55vh] animate-fade-in-up">
      {/* Hero Text */}
      <div className="text-center mb-12 max-w-2xl">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-heading font-black tracking-tight text-foreground leading-none mb-5">
          Redact Indian PII
        </h1>
        <p className="text-base sm:text-lg text-muted-foreground leading-relaxed">
          Upload a Word document and instantly replace all Indian personally identifiable
          information with categorized placeholders, making it safe for LLM processing.
        </p>
      </div>

      {/* Drop Zone */}
      <div
        data-testid="upload-zone"
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        onDragEnter={onDragEnter}
        onDragOver={prevent}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`
          w-full max-w-xl border-2 border-dashed rounded-xl p-14
          flex flex-col items-center justify-center cursor-pointer
          transition-all duration-300
          ${dragging
            ? "upload-zone-active border-primary bg-primary/5"
            : "border-muted-foreground/20 hover:border-primary/40 hover:bg-primary/[0.03]"
          }
        `}
      >
        <div className="w-14 h-14 rounded-xl bg-secondary/80 flex items-center justify-center mb-5">
          {dragging ? (
            <FileText className="w-7 h-7 text-primary" strokeWidth={1.5} />
          ) : (
            <Upload className="w-7 h-7 text-muted-foreground" strokeWidth={1.5} />
          )}
        </div>
        <p className="font-heading font-bold text-foreground mb-1.5">
          {dragging ? "Drop to scan" : "Drop your .docx here"}
        </p>
        <p className="text-sm text-muted-foreground">or click to browse &middot; max 10 MB</p>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        className="hidden"
        data-testid="file-input"
        onChange={(e) => e.target.files?.[0] && onFileSelect(e.target.files[0])}
      />
    </div>
  );
}
