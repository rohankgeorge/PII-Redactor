import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import Header from "@/components/Header";
import PrivacyFooter from "@/components/PrivacyFooter";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
const API = `${BACKEND_URL}/api`;

const MODE_LABELS = {
  FORCE: "Always Redact",
  ALLOW: "Never Redact",
};

export default function RuleLibrary() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [term, setTerm] = useState("");
  const [mode, setMode] = useState("FORCE");
  const [filter, setFilter] = useState("");

  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/rules`);
      setRules(data?.rules || []);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to load rule library");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  const createRule = useCallback(async () => {
    if (!term.trim()) {
      toast.error("Please enter a term first");
      return;
    }
    setSaving(true);
    try {
      await axios.post(`${API}/rules`, { term, mode, enabled: true });
      toast.success(`${MODE_LABELS[mode]} term added`);
      setTerm("");
      await loadRules();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not add rule");
    } finally {
      setSaving(false);
    }
  }, [term, mode, loadRules]);

  const deleteRule = useCallback(async (ruleId) => {
    try {
      await axios.delete(`${API}/rules/${ruleId}`);
      setRules((prev) => prev.filter((r) => r.id !== ruleId));
      toast.success("Rule deleted");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not delete rule");
    }
  }, []);

  const toggleEnabled = useCallback(async (rule) => {
    try {
      const { data } = await axios.put(`${API}/rules/${rule.id}`, {
        enabled: !rule.enabled,
      });
      setRules((prev) => prev.map((r) => (r.id === rule.id ? data.rule : r)));
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not update rule");
    }
  }, []);

  const updateRule = useCallback(async (rule, updates) => {
    try {
      const { data } = await axios.put(`${API}/rules/${rule.id}`, updates);
      setRules((prev) => prev.map((r) => (r.id === rule.id ? data.rule : r)));
      toast.success("Rule updated");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not update rule");
    }
  }, []);

  const filteredRules = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return rules;
    return rules.filter((r) => r.term.toLowerCase().includes(q) || r.mode.toLowerCase().includes(q));
  }, [rules, filter]);

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-6">
        <div className="space-y-2">
          <h1 className="text-3xl font-heading font-bold">Redaction Rules Library</h1>
          <p className="text-muted-foreground">
            Manage offline local rules for <strong>Always Redact</strong> and <strong>Never Redact</strong> terms.
          </p>
        </div>

        <Card>
          <CardContent className="pt-6 space-y-4">
            <h2 className="font-semibold">Add new term</h2>
            <div className="grid grid-cols-1 md:grid-cols-[1fr_220px_auto] gap-3">
              <Input
                value={term}
                onChange={(e) => setTerm(e.target.value)}
                placeholder="Enter a term or phrase"
                data-testid="rule-term-input"
              />
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                className="h-10 rounded-md border border-input bg-background px-3 text-sm"
                data-testid="rule-mode-select"
              >
                <option value="FORCE">Always Redact</option>
                <option value="ALLOW">Never Redact</option>
              </select>
              <Button onClick={createRule} disabled={saving} data-testid="rule-add-btn">
                {saving ? "Saving..." : "Add Rule"}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6 space-y-4">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <h2 className="font-semibold">Current rules</h2>
              <Input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filter by term or mode"
                className="md:max-w-sm"
              />
            </div>

            {loading ? (
              <p className="text-muted-foreground">Loading rules...</p>
            ) : !filteredRules.length ? (
              <p className="text-muted-foreground">No rules found.</p>
            ) : (
              <div className="space-y-3">
                {filteredRules.map((rule) => (
                  <div key={rule.id} className="rounded-lg border border-border/70 p-3 space-y-3" data-testid="rule-row">
                    <div className="grid grid-cols-1 md:grid-cols-[1fr_210px_130px_80px] gap-2">
                      <Input
                        value={rule.term}
                        onChange={(e) => {
                          const value = e.target.value;
                          setRules((prev) => prev.map((r) => (r.id === rule.id ? { ...r, term: value } : r)));
                        }}
                      />
                      <select
                        value={rule.mode}
                        onChange={(e) => {
                          const value = e.target.value;
                          setRules((prev) => prev.map((r) => (r.id === rule.id ? { ...r, mode: value } : r)));
                        }}
                        className="h-10 rounded-md border border-input bg-background px-3 text-sm"
                      >
                        <option value="FORCE">Always Redact</option>
                        <option value="ALLOW">Never Redact</option>
                      </select>
                      <Button
                        variant={rule.enabled ? "default" : "secondary"}
                        onClick={() => toggleEnabled(rule)}
                      >
                        {rule.enabled ? "Enabled" : "Disabled"}
                      </Button>
                      <Button variant="outline" onClick={() => deleteRule(rule.id)}>
                        Delete
                      </Button>
                    </div>
                    <div className="flex justify-end">
                      <Button onClick={() => updateRule(rule, { term: rule.term, mode: rule.mode })}>Save Changes</Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
      <PrivacyFooter />
    </div>
  );
}
