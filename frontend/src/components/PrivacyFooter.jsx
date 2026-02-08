import { Lock, Cpu, ShieldCheck } from "lucide-react";

export default function PrivacyFooter() {
  return (
    <footer className="border-t border-border/60 mt-auto" data-testid="privacy-footer">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col md:flex-row items-center justify-center gap-6 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" strokeWidth={1.5} />
            Documents processed in-memory &mdash; never stored
          </span>
          <span className="hidden md:inline text-border">|</span>
          <span className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5" strokeWidth={1.5} />
            Rule-based detection &mdash; no data sent to external AI
          </span>
          <span className="hidden md:inline text-border">|</span>
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" strokeWidth={1.5} />
            16+ Indian PII categories
          </span>
        </div>
      </div>
    </footer>
  );
}
