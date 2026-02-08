import {
  Download, RotateCcw, ShieldCheck, AlertTriangle, FileSpreadsheet,
  Fingerprint, CreditCard, Phone, Mail, Globe, CheckCircle2,
  Building2, Receipt, User, MapPin, Hash, Car, FileCheck2,
  Wallet, CalendarDays, Landmark, Tag, MapPinned, FileDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

const ICON_MAP = {
  AADHAAR_NUMBER: Fingerprint,
  PAN_NUMBER: CreditCard,
  PHONE_NUMBER: Phone,
  EMAIL: Mail,
  PASSPORT_NUMBER: Globe,
  VOTER_ID: CheckCircle2,
  IFSC_CODE: Building2,
  GST_NUMBER: Receipt,
  NAME: User,
  LOCATION: MapPin,
  PIN_CODE: Hash,
  VEHICLE_REGISTRATION: Car,
  DRIVING_LICENSE: FileCheck2,
  UPI_ID: Wallet,
  DATE_OF_BIRTH: CalendarDays,
  BANK_ACCOUNT: Landmark,
  ADDRESS: MapPinned,
};

function prettify(key) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function aggregateStats(results) {
  const agg = {};
  results.forEach((r) => {
    Object.entries(r.result?.stats || {}).forEach(([k, v]) => {
      agg[k] = (agg[k] || 0) + v;
    });
  });
  return Object.entries(agg).sort((a, b) => b[1] - a[1]);
}

export default function ResultsPanel({ results = [], onDownload, onDownloadAll, onExportAudit, onReset, hasError }) {
  if (hasError || !results.length || results.every((r) => r.error)) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[55vh] animate-fade-in-up" data-testid="error-state">
        <AlertTriangle className="w-16 h-16 text-destructive mb-5" strokeWidth={1.5} />
        <h3 className="text-xl font-heading font-bold text-foreground mb-2">Processing Failed</h3>
        <p className="text-muted-foreground mb-8 text-center max-w-md">
          Something went wrong while scanning your document(s). Please try again.
        </p>
        <Button onClick={onReset} data-testid="try-again-btn">Try Again</Button>
      </div>
    );
  }

  const successResults = results.filter((r) => r.result);
  const totalPII = successResults.reduce((s, r) => s + (r.result?.total || 0), 0);
  const aggEntries = aggregateStats(successResults);
  const isMulti = results.length > 1;

  return (
    <div className="animate-fade-in-up space-y-10" data-testid="results-panel">
      {/* Summary */}
      <div className="text-center">
        <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-emerald-500/10 flex items-center justify-center">
          <ShieldCheck className="w-9 h-9 text-emerald-500" strokeWidth={1.5} />
        </div>
        <h2 className="text-3xl md:text-4xl font-heading font-bold tracking-tight text-foreground mb-2">
          <span className="font-mono text-primary">{totalPII}</span> PII Items Redacted
        </h2>
        <p className="text-muted-foreground">
          {isMulti
            ? `Across ${successResults.length} document(s) — ready for LLM processing.`
            : "Your document is ready for LLM processing."}
        </p>
      </div>

      {/* Combined Stats Grid */}
      {aggEntries.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 max-w-4xl mx-auto" data-testid="stats-grid">
          {aggEntries.map(([key, count], i) => {
            const Icon = ICON_MAP[key] || Tag;
            return (
              <Card key={key} className={`bg-card border-border hover:border-primary/40 transition-colors stagger-${Math.min(i + 1, 8)}`}>
                <CardContent className="p-5 flex items-start gap-3">
                  <div className="w-9 h-9 shrink-0 rounded-lg bg-secondary flex items-center justify-center">
                    <Icon className="w-4 h-4 text-primary" strokeWidth={1.5} />
                  </div>
                  <div>
                    <p className="text-2xl font-mono font-bold text-foreground leading-none">{count}</p>
                    <p className="text-xs text-muted-foreground mt-1 leading-snug">{prettify(key)}</p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {totalPII === 0 && (
        <div className="text-center py-8">
          <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 px-4 py-1.5">
            No PII Detected — Document(s) are clean
          </Badge>
        </div>
      )}

      {/* Per-file breakdown for batch */}
      {isMulti && (
        <div className="max-w-3xl mx-auto space-y-3" data-testid="per-file-results">
          <h3 className="text-sm font-heading font-bold text-muted-foreground uppercase tracking-wider mb-3">Per-file Results</h3>
          {results.map((r, i) => (
            <div key={i} className="flex items-center justify-between gap-4 py-3 px-4 rounded-lg bg-card border border-border">
              <div className="min-w-0 flex-1">
                <p className="font-mono text-sm text-foreground truncate">{r.fileName}</p>
                {r.error ? (
                  <p className="text-xs text-destructive mt-0.5">{r.error}</p>
                ) : (
                  <p className="text-xs text-muted-foreground mt-0.5">{r.result?.total || 0} PII items</p>
                )}
              </div>
              {r.result && (
                <Button variant="ghost" size="sm" onClick={() => onDownload(i)} data-testid={`download-file-${i}`}>
                  <FileDown className="w-4 h-4" />
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      <Separator className="max-w-3xl mx-auto" />

      {/* Actions */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2" data-testid="action-buttons">
        {totalPII > 0 && (
          <Button
            onClick={isMulti ? onDownloadAll : () => onDownload(0)}
            size="lg"
            className="shadow-[0_0_20px_rgba(59,130,246,0.25)] hover:shadow-[0_0_30px_rgba(59,130,246,0.35)] transition-shadow"
            data-testid="download-btn"
          >
            <Download className="w-4 h-4 mr-2" />
            {isMulti ? "Download All Redacted" : "Download Redacted Document"}
          </Button>
        )}
        <Button variant="secondary" size="lg" onClick={onExportAudit} data-testid="export-audit-btn">
          <FileSpreadsheet className="w-4 h-4 mr-2" /> Export Audit Report
        </Button>
        <Button variant="ghost" size="lg" onClick={onReset} data-testid="start-over-btn">
          <RotateCcw className="w-4 h-4 mr-2" /> Start Over
        </Button>
      </div>
    </div>
  );
}
