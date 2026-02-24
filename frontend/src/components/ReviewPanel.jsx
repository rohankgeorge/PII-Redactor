import { useMemo, useState, useCallback } from "react";
import {
  AlertTriangle, CheckSquare, Square, ShieldCheck, RotateCcw,
  ChevronDown, ChevronRight, Pencil, Plus, X, List, Layers,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";

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
  forceRedactTerms = [],
  onForceRedactTermsChange,
  placeholderOverrides = {},
  onPlaceholderOverridesChange,
}) {
  const [viewMode, setViewMode] = useState("flat"); // "flat" | "grouped"
  const [expandedGroups, setExpandedGroups] = useState(new Set());
  const [newForceTerm, setNewForceTerm] = useState("");
  const [editingCandidateId, setEditingCandidateId] = useState(null);
  const [editText, setEditText] = useState("");

  // ── Selection helpers ────────────────────────────────────
  const selection = useMemo(() => {
    const selectedSet = new Set(selectedCandidateIds);
    return {
      selectedSet,
      selectedCount: selectedSet.size,
      totalCount: candidates.length,
      deselectedCount: Math.max(candidates.length - selectedSet.size, 0),
    };
  }, [candidates.length, selectedCandidateIds]);

  const toggleCandidate = (candidateId) => {
    const current = new Set(selectedCandidateIds);
    if (current.has(candidateId)) {
      current.delete(candidateId);
    } else {
      current.add(candidateId);
    }
    onSelectionChange(Array.from(current));
  };

  const selectAll = () => {
    onSelectionChange(candidates.map((c) => c.candidate_id));
  };

  const clearAll = () => {
    onSelectionChange([]);
  };

  // ── Category data ────────────────────────────────────────
  const categories = useMemo(() => {
    const map = {};
    candidates.forEach((c) => {
      const cat = c.category || "UNKNOWN";
      if (!map[cat]) map[cat] = [];
      map[cat].push(c.candidate_id);
    });
    return Object.entries(map).sort((a, b) => b[1].length - a[1].length);
  }, [candidates]);

  const toggleCategory = (category, candidateIds) => {
    const current = new Set(selectedCandidateIds);
    const allSelected = candidateIds.every((id) => current.has(id));
    if (allSelected) {
      candidateIds.forEach((id) => current.delete(id));
    } else {
      candidateIds.forEach((id) => current.add(id));
    }
    onSelectionChange(Array.from(current));
  };

  // ── Grouped view data ───────────────────────────────────
  const groups = useMemo(() => {
    const map = {};
    candidates.forEach((c) => {
      const key = (c.original_text || "").toLowerCase();
      if (!map[key]) map[key] = { term: c.original_text, candidates: [] };
      map[key].candidates.push(c);
    });
    return Object.values(map).sort((a, b) => b.candidates.length - a.candidates.length);
  }, [candidates]);

  const toggleGroup = (group) => {
    const current = new Set(selectedCandidateIds);
    const ids = group.candidates.map((c) => c.candidate_id);
    const allSelected = ids.every((id) => current.has(id));
    if (allSelected) {
      ids.forEach((id) => current.delete(id));
    } else {
      ids.forEach((id) => current.add(id));
    }
    onSelectionChange(Array.from(current));
  };

  const toggleGroupExpand = (term) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(term)) next.delete(term);
      else next.add(term);
      return next;
    });
  };

  // ── Force-redact helpers ─────────────────────────────────
  const addForceTerm = useCallback(() => {
    const term = newForceTerm.trim();
    if (!term || forceRedactTerms.includes(term)) return;
    onForceRedactTermsChange?.([...forceRedactTerms, term]);
    setNewForceTerm("");
  }, [newForceTerm, forceRedactTerms, onForceRedactTermsChange]);

  const removeForceTerm = useCallback((term) => {
    onForceRedactTermsChange?.(forceRedactTerms.filter((t) => t !== term));
  }, [forceRedactTerms, onForceRedactTermsChange]);

  // ── Placeholder override helpers ─────────────────────────
  const startEditing = (candidateId, currentPlaceholder) => {
    setEditingCandidateId(candidateId);
    setEditText(placeholderOverrides[candidateId] || currentPlaceholder || "");
  };

  const saveOverride = () => {
    if (!editingCandidateId) return;
    const text = editText.trim();
    const updated = { ...placeholderOverrides };
    if (text) {
      updated[editingCandidateId] = text;
    } else {
      delete updated[editingCandidateId];
    }
    onPlaceholderOverridesChange?.(updated);
    setEditingCandidateId(null);
    setEditText("");
  };

  const cancelEditing = () => {
    setEditingCandidateId(null);
    setEditText("");
  };

  // ── Candidate card (shared by flat + grouped views) ──────
  const renderCandidate = (candidate) => {
    const isSelected = selection.selectedSet.has(candidate.candidate_id);
    const isEditing = editingCandidateId === candidate.candidate_id;
    const override = placeholderOverrides[candidate.candidate_id];

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
                <Badge variant={override ? "default" : "outline"} className="font-mono text-xs">
                  {override || candidate.placeholder}
                </Badge>
                {override && (
                  <Badge variant="outline" className="font-mono text-xs line-through opacity-50">
                    {candidate.placeholder}
                  </Badge>
                )}
              </div>
              <p className="text-sm text-foreground break-words">{candidate.original_text}</p>
              {candidate.location && (
                <p className="text-xs text-muted-foreground">Location: {candidate.location}</p>
              )}
              <div className="flex items-center gap-1">
                {isEditing ? (
                  <div className="flex items-center gap-2 w-full">
                    <Input
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") saveOverride(); if (e.key === "Escape") cancelEditing(); }}
                      className="h-7 text-xs flex-1"
                      placeholder="Custom placeholder text..."
                      autoFocus
                      data-testid="placeholder-edit-input"
                    />
                    <Button variant="ghost" size="sm" className="h-7 px-2" onClick={saveOverride} data-testid="placeholder-save-btn">Save</Button>
                    <Button variant="ghost" size="sm" className="h-7 px-2" onClick={cancelEditing}>Cancel</Button>
                  </div>
                ) : (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-xs text-muted-foreground"
                    onClick={() => startEditing(candidate.candidate_id, candidate.placeholder)}
                    data-testid={`edit-placeholder-${candidate.candidate_id}`}
                  >
                    <Pencil className="w-3 h-3 mr-1" /> Edit placeholder
                  </Button>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="animate-fade-in-up space-y-8" data-testid="review-panel">
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-primary/10 flex items-center justify-center">
          <ShieldCheck className="w-9 h-9 text-primary" strokeWidth={1.5} />
        </div>
        <h2 className="text-3xl md:text-4xl font-heading font-bold tracking-tight text-foreground">Review before redaction</h2>
        <p className="text-muted-foreground text-sm sm:text-base">
          Candidate-level control for <span className="font-mono">{fileName}</span>
        </p>
      </div>

      {/* Selection summary */}
      <Card className="max-w-4xl mx-auto">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Selection summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">Candidates: {selection.totalCount}</Badge>
            <Badge variant="secondary">Selected: {selection.selectedCount}</Badge>
            <Badge variant="outline">Excluded: {selection.deselectedCount}</Badge>
            {forceRedactTerms.length > 0 && (
              <Badge variant="secondary">Force-redact terms: {forceRedactTerms.length}</Badge>
            )}
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
            <Separator orientation="vertical" className="h-8" />
            <Button
              variant={viewMode === "flat" ? "secondary" : "outline"}
              size="sm"
              onClick={() => setViewMode("flat")}
              data-testid="view-flat"
            >
              <List className="w-4 h-4 mr-1" /> Flat
            </Button>
            <Button
              variant={viewMode === "grouped" ? "secondary" : "outline"}
              size="sm"
              onClick={() => setViewMode("grouped")}
              data-testid="view-grouped"
            >
              <Layers className="w-4 h-4 mr-1" /> Grouped
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

      {/* Feature 3.2: Category toggles */}
      <Card className="max-w-4xl mx-auto" data-testid="category-toggles">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Category toggles</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {categories.map(([category, candidateIds]) => {
            const allSelected = candidateIds.every((id) => selection.selectedSet.has(id));
            const someSelected = !allSelected && candidateIds.some((id) => selection.selectedSet.has(id));
            return (
              <div key={category} className="flex items-center justify-between gap-4 py-1">
                <div className="flex items-center gap-2">
                  <Label className="text-sm font-semibold text-foreground">{prettify(category)}</Label>
                  <Badge variant="outline" className="text-xs">{candidateIds.length}</Badge>
                  {someSelected && <Badge variant="secondary" className="text-xs">partial</Badge>}
                </div>
                <Switch
                  checked={allSelected}
                  onCheckedChange={() => toggleCategory(category, candidateIds)}
                  data-testid={`category-toggle-${category}`}
                />
              </div>
            );
          })}
          {categories.length === 0 && (
            <p className="text-sm text-muted-foreground">No categories detected.</p>
          )}
        </CardContent>
      </Card>

      {/* Feature 3.3: Inline force-redact */}
      <Card className="max-w-4xl mx-auto" data-testid="force-redact-section">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Force-redact custom terms</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Add words or phrases that should always be redacted, even if the engine did not detect them.
          </p>
          <div className="flex gap-2">
            <Input
              value={newForceTerm}
              onChange={(e) => setNewForceTerm(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") addForceTerm(); }}
              placeholder="Type a term to force-redact..."
              className="flex-1"
              data-testid="force-redact-input"
            />
            <Button size="sm" onClick={addForceTerm} disabled={!newForceTerm.trim()} data-testid="force-redact-add-btn">
              <Plus className="w-4 h-4 mr-1" /> Add
            </Button>
          </div>
          {forceRedactTerms.length > 0 && (
            <div className="flex flex-wrap gap-2" data-testid="force-redact-tags">
              {forceRedactTerms.map((term) => (
                <Badge key={term} variant="secondary" className="gap-1 pr-1">
                  {term}
                  <button
                    onClick={() => removeForceTerm(term)}
                    className="ml-1 rounded-full hover:bg-destructive/20 p-0.5"
                    data-testid={`force-redact-remove-${term}`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Candidate list */}
      <div className="max-w-4xl mx-auto space-y-3">
        {candidates.length === 0 ? (
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">No redaction candidates were detected for this file.</p>
            </CardContent>
          </Card>
        ) : viewMode === "flat" ? (
          /* Feature: Flat view (original behavior + edit buttons) */
          candidates.map(renderCandidate)
        ) : (
          /* Feature 3.1: Grouped view */
          groups.map((group) => {
            const key = group.term.toLowerCase();
            const isExpanded = expandedGroups.has(key);
            const ids = group.candidates.map((c) => c.candidate_id);
            const allSelected = ids.every((id) => selection.selectedSet.has(id));

            return (
              <Card key={key} className={allSelected ? "border-primary/50" : "border-border"} data-testid={`group-${key}`}>
                <CardContent className="p-4">
                  <div className="flex items-center gap-3">
                    <Checkbox
                      checked={allSelected}
                      onCheckedChange={() => toggleGroup(group)}
                      data-testid={`group-checkbox-${key}`}
                    />
                    <button
                      className="flex items-center gap-2 flex-1 text-left"
                      onClick={() => toggleGroupExpand(key)}
                    >
                      {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      <span className="text-sm font-medium text-foreground break-words">{group.term}</span>
                      <Badge variant="outline" className="text-xs">{group.candidates.length} occurrence{group.candidates.length > 1 ? "s" : ""}</Badge>
                    </button>
                  </div>
                  {isExpanded && (
                    <div className="mt-3 ml-8 space-y-2">
                      {group.candidates.map(renderCandidate)}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      <Separator className="max-w-4xl mx-auto" />

      {/* Actions */}
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
