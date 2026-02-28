import { useState } from "react";
import { motion } from "framer-motion";
import { Search, Loader2, X, FileText } from "lucide-react";
import { searchTranscripts, type SearchHit } from "../lib/api";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [searchType, setSearchType] = useState("fulltext");
  const [results, setResults] = useState<SearchHit[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await searchTranscripts({
        query: query.trim(),
        search_type: searchType,
        limit: 50,
      });
      setResults(data.results);
      setTotal(data.total);
      setSearched(true);
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Search Transcripts</h1>
        <p className="text-sm text-white/50 mt-1">
          Full-text search across all transcript segments
        </p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search transcripts…"
            className="input-field !pl-10"
            autoFocus
          />
        </div>
        <select
          value={searchType}
          onChange={(e) => setSearchType(e.target.value)}
          className="input-field !w-auto"
        >
          <option value="fulltext">Full Text</option>
          <option value="exact">Exact</option>
          <option value="fuzzy">Fuzzy</option>
          <option value="regex">Regex</option>
        </select>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-5 py-2.5 rounded-lg bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white transition-colors flex items-center gap-2"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          Search
        </button>
      </form>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400 text-sm flex items-center justify-between">
          {error}
          <button onClick={() => setError("")}><X className="w-4 h-4" /></button>
        </div>
      )}

      {searched && !loading && (
        <p className="text-sm text-white/40">
          {total} result(s) for "<span className="text-white/70">{query}</span>"
        </p>
      )}

      {searched && !loading && results.length === 0 && (
        <div className="border border-white/10 rounded-xl p-12 text-center">
          <FileText className="w-10 h-10 text-white/20 mx-auto mb-4" />
          <p className="text-white/40">No matching segments found</p>
          <p className="text-xs text-white/30 mt-2">
            Transcripts appear here once streams produce segments indexed in Elasticsearch
          </p>
        </div>
      )}

      {results.length > 0 && (
        <div className="grid gap-3">
          {results.map((hit, i) => (
            <motion.div
              key={hit.segment_id ?? i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className="border border-white/10 rounded-xl p-4 bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-sm text-white" dangerouslySetInnerHTML={{ __html: hit.text }} />
                  <div className="flex items-center gap-3 mt-2 text-xs text-white/30">
                    {hit.speaker_id && <span>Speaker: {hit.speaker_id}</span>}
                    {hit.stream_name && <span>Stream: {hit.stream_name}</span>}
                    {hit.sentiment_label && (
                      <span className="capitalize">{hit.sentiment_label}</span>
                    )}
                    {hit.score != null && (
                      <span>Score: {hit.score.toFixed(2)}</span>
                    )}
                  </div>
                </div>
                <span className="text-xs text-white/30 whitespace-nowrap">
                  {hit.timestamp ? new Date(hit.timestamp).toLocaleString() : "—"}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
