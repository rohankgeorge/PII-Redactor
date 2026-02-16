import { useMemo } from "react";
import { AlertTriangle, CheckSquare, Square, ShieldCheck, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

function prettify(key) {
  return (key || "UNKNOWN").replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function ReviewPanel({
  fileName,
  candidates,
  selectedCandidateIds,
  reviewPayload,
  policyOptions,
  onPolicyChange,
  onSelectionChange,
  onApply,
  onReset,
}) {
  // Computes selection counts so the review UI can communicate impact before applying changes.
  const selection = useMemo(() => {
    const selectedSet = new Set(selectedCandidateIds);
    return {
      selectedSet,
      selectedCount: selectedSet.size,
      totalCount: candidates.length,
      deselectedCount: Math.max(candidates.length - selectedSet.size, 0),
    };
  }, [candidates.length, selectedCandidateIds]);

  // Toggles policy switches for location and country redaction behavior.
  const updatePolicy = (key, value) => {
    if (!onPolicyChange) {
      return;
    }
    onPolicyChange({
      ...(policyOptions || {}),
      [key]: value,
    });
  };

  // Toggles an individual candidate while keeping state immutable for predictable React renders.
  const toggleCandidate = (candidateId) => {
    const current = new Set(selectedCandidateIds);
    if (current.has(candidateId)) {
      current.delete(candidateId);
    } else {
      current.add(candidateId);
    }
    onSelectionChange(Array.from(current));
  };

  // Selects all current candidates in a single action.
  const selectAll = () => {
    onSelectionChange(candidates.map((candidate) => candidate.candidate_id));
  };

  // Deselects all candidates so the user can quickly apply no redactions if desired.
  const clearAll = () => {
    onSelectionChange([]);
  };

  return (
    <div className="animate-fade-in-up space-y-8" data-testid="review-panel">
      <div className="text-center space-y-2">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-primary/10 flex items-center justify-center">
          <ShieldCheck className="w-9 h-9 text-primary" strokeWidth={1.5} />
        </div>
        <h2 className="text-3xl md:text-4xl font-heading font-bold tracking-tight text-foreground">Review before redaction</h2>
        <p className="text-muted-foreground text-sm sm:text-base">
          Candidate-level control for <span className="font-mono">{fileName}</span>
        </p>
      </div>

      <Card className="max-w-4xl mx-auto">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Selection summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">Candidates: {selection.totalCount}</Badge>
            <Badge variant="secondary">Selected: {selection.selectedCount}</Badge>
            <Badge variant="outline">Excluded: {selection.deselectedCount}</Badge>
            {reviewPayload?.review_required && (
              <Badge variant="destructive">Potential leaks: {reviewPayload?.potential_leak_count || 0}</Badge>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={selectAll}>
              <CheckSquare className="w-4 h-4 mr-2" /> Select All
            </Button>
            <Button variant="outline" size="sm" onClick={clearAll}>
              <Square className="w-4 h-4 mr-2" /> Clear All
            </Button>
          </div>

          {reviewPayload?.review_required && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive flex gap-2 items-start">
              <AlertTriangle className="w-4 h-4 mt-0.5" />
              <span>
                Manual review suggested for {reviewPayload?.potential_leak_count || 0} potential leak item(s).
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="max-w-4xl mx-auto">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Policy toggles</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <Label htmlFor="policy-location-toggle" className="text-sm font-semibold text-foreground">
                Redact locations
              </Label>
              <p className="text-xs text-muted-foreground">
                Turn off to keep location and address candidates unredacted.
              </p>
            </div>
            <Switch
              id="policy-location-toggle"
              checked={policyOptions?.redactLocations ?? true}
              onCheckedChange={(value) => updatePolicy("redactLocations", value)}
              data-testid="policy-location-toggle"
            />
          </div>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <Label htmlFor="policy-country-toggle" className="text-sm font-semibold text-foreground">
                Redact countries
              </Label>
              <p className="text-xs text-muted-foreground">
                Turn off to keep country mentions while still redacting non-country locations.
              </p>
            </div>
            <Switch
              id="policy-country-toggle"
              checked={policyOptions?.redactCountries ?? true}
              onCheckedChange={(value) => updatePolicy("redactCountries", value)}
              data-testid="policy-country-toggle"
            />
          </div>
        </CardContent>
      </Card>

      <div className="max-w-4xl mx-auto space-y-3">
        {candidates.length === 0 ? (
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">No redaction candidates were detected for this file.</p>
            </CardContent>
          </Card>
        ) : (
          candidates.map((candidate) => {
            const isSelected = selection.selectedSet.has(candidate.candidate_id);
            return (
              <Card key={candidate.candidate_id} className={isSelected ? "border-primary/50" : "border-border"}>
                <CardContent className="p-4 sm:p-5">
                  <div className="flex items-start gap-3">
                    <Checkbox
                      id={candidate.candidate_id}
                      checked={isSelected}
                      onCheckedChange={() => toggleCandidate(candidate.candidate_id)}
                    />
                    <div className="min-w-0 flex-1 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="secondary">{prettify(candidate.category)}</Badge>
                        <Badge variant="outline" className="font-mono text-xs">{candidate.placeholder}</Badge>
                        <Badge variant="outline" className="font-mono text-xs">{candidate.candidate_id}</Badge>
                      </div>
                      <p className="text-sm text-foreground break-words">{candidate.original_text}</p>
                      {candidate.location && (
                        <p className="text-xs text-muted-foreground">Location: {candidate.location}</p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      <Separator className="max-w-4xl mx-auto" />

      <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
        <Button onClick={() => onApply(selectedCandidateIds, policyOptions)} size="lg" data-testid="apply-redaction-btn">
          Apply Selected Redactions
        </Button>
        <Button variant="ghost" size="lg" onClick={onReset} data-testid="review-start-over-btn">
          <RotateCcw className="w-4 h-4 mr-2" /> Start Over
        </Button>
      </div>
    </div>
  );
}
