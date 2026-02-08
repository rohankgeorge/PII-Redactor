import { useEffect, useState } from "react";
import { Loader2, ScanSearch } from "lucide-react";
import { Progress } from "@/components/ui/progress";

export default function ProcessingState({ fileName }) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setProgress((p) => (p >= 88 ? 88 : p + Math.random() * 12));
    }, 250);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-[55vh] animate-fade-in-up" data-testid="processing-state">
      <div className="relative mb-8">
        <div className="w-20 h-20 rounded-2xl bg-secondary/80 flex items-center justify-center animate-pulse_glow">
          <ScanSearch className="w-10 h-10 text-primary" strokeWidth={1.5} />
        </div>
        <Loader2 className="absolute -top-2 -right-2 w-6 h-6 text-primary animate-spin" strokeWidth={2} />
      </div>

      <h3 className="text-xl font-heading font-bold text-foreground mb-2">Scanning Document</h3>
      <p className="font-mono text-sm text-muted-foreground mb-8 max-w-xs truncate">{fileName}</p>

      <div className="w-full max-w-sm">
        <Progress value={progress} className="h-1.5" />
        <p className="text-xs text-muted-foreground mt-3 text-center">
          Detecting Aadhaar, PAN, names, addresses and more&hellip;
        </p>
      </div>
    </div>
  );
}
