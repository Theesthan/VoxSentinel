import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus,
  Trash2,
  RefreshCw,
  Shield,
  Loader2,
  X,
  Pencil,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import {
  listRules,
  createRule,
  updateRule,
  deleteRule,
  type Rule,
  type RuleCreateRequest,
} from "../lib/api";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "text-red-400 border-red-500/30",
  high: "text-orange-400 border-orange-500/30",
  medium: "text-yellow-400 border-yellow-500/30",
  low: "text-blue-400 border-blue-500/30",
};

export default function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editRule, setEditRule] = useState<Rule | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listRules();
      setRules(data.rules);
      setTotal(data.total);
      setError("");
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleCreate = async (form: RuleCreateRequest) => {
    setSaving(true);
    try {
      await createRule(form);
      setShowCreate(false);
      await refresh();
    } catch (e: unknown) { setError(String(e)); }
    finally { setSaving(false); }
  };

  const handleUpdate = async (id: string, body: Partial<RuleCreateRequest>) => {
    setSaving(true);
    try {
      await updateRule(id, body);
      setEditRule(null);
      await refresh();
    } catch (e: unknown) { setError(String(e)); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteRule(id);
      await refresh();
    } catch (e: unknown) { setError(String(e)); }
  };

  const handleToggle = async (r: Rule) => {
    try {
      await updateRule(r.rule_id, { enabled: !r.enabled });
      await refresh();
    } catch (e: unknown) { setError(String(e)); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Keyword Rules</h1>
          <p className="text-sm text-white/50 mt-1">{total} rule(s)</p>
        </div>
        <div className="flex gap-2">
          <button onClick={refresh} className="p-2 rounded-lg border border-white/10 text-white/60 hover:text-white hover:bg-white/5 transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors">
            <Plus className="w-4 h-4" /> New Rule
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400 text-sm flex items-center justify-between">
          {error}
          <button onClick={() => setError("")}><X className="w-4 h-4" /></button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 text-white/40 animate-spin" />
        </div>
      ) : rules.length === 0 ? (
        <div className="border border-white/10 rounded-xl p-12 text-center">
          <Shield className="w-10 h-10 text-white/20 mx-auto mb-4" />
          <p className="text-white/40">No keyword rules</p>
          <button onClick={() => setShowCreate(true)} className="mt-4 text-red-400 hover:text-red-300 text-sm">
            Create your first rule
          </button>
        </div>
      ) : (
        <div className="border border-white/10 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-white/40 text-left">
                <th className="px-4 py-3 font-medium">Keyword</th>
                <th className="px-4 py-3 font-medium">Rule Set</th>
                <th className="px-4 py-3 font-medium">Match</th>
                <th className="px-4 py-3 font-medium">Severity</th>
                <th className="px-4 py-3 font-medium">Category</th>
                <th className="px-4 py-3 font-medium">Enabled</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <motion.tr
                  key={r.rule_id}
                  layout
                  className="border-b border-white/5 hover:bg-white/[0.03] transition-colors"
                >
                  <td className="px-4 py-3 text-white font-mono">{r.keyword}</td>
                  <td className="px-4 py-3 text-white/60">{r.rule_set_name}</td>
                  <td className="px-4 py-3 text-white/60 capitalize">{r.match_type}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full border capitalize ${SEVERITY_COLORS[r.severity] ?? "text-white/50 border-white/10"}`}>
                      {r.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-white/60 capitalize">{r.category}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => handleToggle(r)} className="text-white/60 hover:text-white transition-colors">
                      {r.enabled ? <ToggleRight className="w-5 h-5 text-green-400" /> : <ToggleLeft className="w-5 h-5 text-white/30" />}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => setEditRule(r)} className="p-1.5 rounded-lg hover:bg-white/10 text-white/40 hover:text-white transition-colors" title="Edit">
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => handleDelete(r.rule_id)} className="p-1.5 rounded-lg hover:bg-white/10 text-red-400 transition-colors" title="Delete">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <AnimatePresence>
        {showCreate && (
          <RuleModal
            title="New Rule"
            onClose={() => setShowCreate(false)}
            onSubmit={(f) => handleCreate(f)}
            loading={saving}
          />
        )}
        {editRule && (
          <RuleModal
            title="Edit Rule"
            initial={editRule}
            onClose={() => setEditRule(null)}
            onSubmit={(f) => handleUpdate(editRule.rule_id, f)}
            loading={saving}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Rule Modal ──

function RuleModal({
  title,
  initial,
  onClose,
  onSubmit,
  loading,
}: {
  title: string;
  initial?: Rule;
  onClose: () => void;
  onSubmit: (form: RuleCreateRequest) => void;
  loading: boolean;
}) {
  const [form, setForm] = useState<RuleCreateRequest>({
    rule_set_name: initial?.rule_set_name ?? "default",
    keyword: initial?.keyword ?? "",
    match_type: initial?.match_type ?? "exact",
    severity: initial?.severity ?? "medium",
    category: initial?.category ?? "general",
    enabled: initial?.enabled ?? true,
  });

  const set = (key: keyof RuleCreateRequest, val: string | boolean | number) =>
    setForm((f) => ({ ...f, [key]: val }));

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg border border-white/10 rounded-xl bg-[#0a0a0a] p-6 space-y-5"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">{title}</h2>
          <button onClick={onClose} className="text-white/40 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        <div className="space-y-4">
          <Field label="Keyword">
            <input value={form.keyword} onChange={(e) => set("keyword", e.target.value)} placeholder="e.g. bomb" className="input-field" />
          </Field>
          <Field label="Rule Set Name">
            <input value={form.rule_set_name} onChange={(e) => set("rule_set_name", e.target.value)} placeholder="default" className="input-field" />
          </Field>
          <div className="grid grid-cols-3 gap-4">
            <Field label="Match Type">
              <select value={form.match_type} onChange={(e) => set("match_type", e.target.value)} className="input-field">
                <option value="exact">Exact</option>
                <option value="fuzzy">Fuzzy</option>
                <option value="regex">Regex</option>
                <option value="phonetic">Phonetic</option>
              </select>
            </Field>
            <Field label="Severity">
              <select value={form.severity} onChange={(e) => set("severity", e.target.value)} className="input-field">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </Field>
            <Field label="Category">
              <select value={form.category} onChange={(e) => set("category", e.target.value)} className="input-field">
                <option value="general">General</option>
                <option value="threat">Threat</option>
                <option value="compliance">Compliance</option>
                <option value="sentiment">Sentiment</option>
              </select>
            </Field>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button onClick={onClose} className="px-4 py-2 rounded-lg border border-white/10 text-white/60 hover:text-white transition-colors">Cancel</button>
          <button
            onClick={() => onSubmit(form)}
            disabled={loading || !form.keyword}
            className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white transition-colors flex items-center gap-2"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {initial ? "Save" : "Create"}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm text-white/50 mb-1.5">{label}</label>
      {children}
    </div>
  );
}
