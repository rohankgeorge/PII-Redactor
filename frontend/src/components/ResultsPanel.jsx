import {
  Download, RotateCcw, ShieldCheck, AlertTriangle,
  Fingerprint, CreditCard, Phone, Mail, Globe, CheckCircle2,
  Building2, Receipt, User, MapPin, Hash, Car, FileCheck2,
  Wallet, CalendarDays, Landmark, Tag, MapPinned,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

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

export default function ResultsPanel({ result, onDownload, onReset, hasError }) {
  if (hasError || !result) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[55vh] animate-fade-in-up" data-testid="error-state">
        <AlertTriangle className="w-16 h-16 text-destructive mb-5" strokeWidth={1.5} />
        <h3 className="text-xl font-heading font-bold text-foreground mb-2">Processing Failed</h3>
        <p className="text-muted-foreground mb-8 text-center max-w-md">
          Something went wrong while scanning your document. Please try again.
        </p>
        <Button onClick={onReset} data-testid="try-again-btn">Try Again</Button>
      </div>
    );
  }

  const { stats, total } = result;
  const entries = Object.entries(stats).sort((a, b) => b[1] - a[1]);

  return (
    <div className="animate-fade-in-up space-y-10" data-testid="results-panel">
      {/* Summary */}
      <div className="text-center">
        <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-emerald-500/10 flex items-center justify-center">
          <ShieldCheck className="w-9 h-9 text-emerald-500" strokeWidth={1.5} />
        </div>
        <h2 className="text-3xl md:text-4xl font-heading font-bold tracking-tight text-foreground mb-2">
          <span className="font-mono text-primary">{total}</span> PII Items Redacted
        </h2>
        <p className="text-muted-foreground">Your document is ready for LLM processing.</p>
      </div>

      {/* Stats Grid */}
      {entries.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 max-w-4xl mx-auto" data-testid="stats-grid">
          {entries.map(([key, count], i) => {
            const Icon = ICON_MAP[key] || Tag;
            return (
              <Card
                key={key}
                className={`bg-card border-border hover:border-primary/40 transition-colors stagger-${i + 1}`}
              >
                <CardContent className="p-5 flex items-start gap-3">
                  <div className="w-9 h-9 shrink-0 rounded-lg bg-secondary flex items-center justify-center">
                    <Icon className="w-4.5 h-4.5 text-primary" strokeWidth={1.5} />
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

      {total === 0 && (
        <div className="text-center py-8">
          <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 px-4 py-1.5">
            No PII Detected — Document is clean
          </Badge>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
        {total > 0 && (
          <Button
            onClick={onDownload}
            size="lg"
            className="shadow-[0_0_20px_rgba(59,130,246,0.25)] hover:shadow-[0_0_30px_rgba(59,130,246,0.35)] transition-shadow"
            data-testid="download-btn"
          >
            <Download className="w-4 h-4 mr-2" /> Download Redacted Document
          </Button>
        )}
        <Button variant="secondary" size="lg" onClick={onReset} data-testid="start-over-btn">
          <RotateCcw className="w-4 h-4 mr-2" /> Start Over
        </Button>
      </div>
    </div>
  );
}
