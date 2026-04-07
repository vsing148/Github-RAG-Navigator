import React, { useState, useEffect } from 'react';
import { Search, Database, GitPullRequest, Loader2, AlertCircle, CheckCircle, ExternalLink } from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function App() {
  const [repos, setRepos] = useState([]);

  const [ingestOwner, setIngestOwner] = useState('');
  const [ingestName, setIngestName] = useState('');
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestStatus, setIngestStatus] = useState(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRepo, setSelectedRepo] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchStatus, setSearchStatus] = useState(null);

  useEffect(() => {
    fetchRepos();
  }, []);

  const fetchRepos = async () => {
    try {
      const res = await fetch(`${API_BASE}/repos`);
      const data = await res.json();
      setRepos(data.repos || []);
      if (data.repos?.length > 0 && !selectedRepo) {
        setSelectedRepo(data.repos[0].repo_name);
      }
    } catch (err) {
      console.error("Failed to fetch repos", err);
    }
  };

  const handleIngest = async (e) => {
    e.preventDefault();
    setIngestLoading(true);
    setIngestStatus(null);
    try {
      const res = await fetch(`${API_BASE}/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_owner: ingestOwner,
          repo_name: ingestName,
          limit: 20
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ingestion failed');

      setIngestStatus({ type: 'success', msg: data.message });
      setIngestOwner('');
      setIngestName('');
      fetchRepos();
    } catch (err) {
      setIngestStatus({ type: 'error', msg: err.message });
    } finally {
      setIngestLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!selectedRepo) return;

    setSearchLoading(true);
    setSearchStatus(null);
    setSearchResults(null);

    const [owner, name] = selectedRepo.split('/');

    try {
      const res = await fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_owner: owner,
          repo_name: name,
          query: searchQuery
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Search failed');

      setSearchResults(data);
    } catch (err) {
      setSearchStatus({ type: 'error', msg: err.message });
    } finally {
      setSearchLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d1117] flex font-sans text-[#c9d1d9]">

      {/* SIDEBAR */}
      <div className="w-72 bg-[#161b22] border-r border-[#30363d] p-6 flex flex-col">
        <div className="flex items-center space-x-2 mb-8">
          <Database className="w-6 h-6 text-[#c9d1d9]" />
          <h1 className="text-xl font-bold text-[#c9d1d9]">RAG Navigator</h1>
        </div>

        <h2 className="text-xs font-semibold text-[#8b949e] uppercase mb-4">Ingested Repositories</h2>
        <div className="space-y-1.5 flex-grow overflow-y-auto pr-2">
          {repos.length === 0 ? (
            <p className="text-sm text-[#8b949e] italic">No repos ingested yet.</p>
          ) : (
            repos.map(repo => (
              <button
                key={repo.repo_name}
                onClick={() => setSelectedRepo(repo.repo_name)}
                className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors border ${selectedRepo === repo.repo_name
                    ? 'bg-[#21262d] text-[#c9d1d9] border-[#30363d] font-semibold shadow-sm'
                    : 'bg-transparent text-[#8b949e] hover:bg-[#21262d] border-transparent'
                  }`}
              >
                <div className="truncate">{repo.repo_name}</div>
                <div className="text-[11px] font-normal text-[#8b949e] mt-0.5">{repo.issue_count} issues indexed</div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 flex flex-col p-8 lg:p-12 max-w-5xl mx-auto space-y-8 overflow-y-auto">

        {/* SECTION 1: INGESTION */}
        <section className="bg-[#161b22] rounded-md shadow-sm border border-[#30363d] p-6">
          <h2 className="text-lg font-semibold text-[#c9d1d9] mb-1">Ingest New Repository</h2>
          <p className="text-sm text-[#8b949e] mb-5">Download GitHub issues and generate vector embeddings.</p>

          <form onSubmit={handleIngest} className="flex flex-col sm:flex-row gap-3 items-start">
            <div className="flex-1 w-full relative">
              <input
                type="text" required placeholder="Owner (e.g. facebook)"
                value={ingestOwner} onChange={(e) => setIngestOwner(e.target.value)}
                className="w-full px-3 py-1.5 rounded-md border border-[#30363d] bg-[#0d1117] focus:bg-[#0d1117] focus:ring-2 focus:ring-[#58a6ff] focus:border-[#58a6ff] outline-none transition-all text-sm text-[#c9d1d9] placeholder-[#8b949e]"
              />
            </div>
            <span className="hidden sm:flex text-[#8b949e] py-1.5">/</span>
            <div className="flex-1 w-full relative">
              <input
                type="text" required placeholder="Repo (e.g. react)"
                value={ingestName} onChange={(e) => setIngestName(e.target.value)}
                className="w-full px-3 py-1.5 rounded-md border border-[#30363d] bg-[#0d1117] focus:bg-[#0d1117] focus:ring-2 focus:ring-[#58a6ff] focus:border-[#58a6ff] outline-none transition-all text-sm text-[#c9d1d9] placeholder-[#8b949e]"
              />
            </div>
            <button
              type="submit" disabled={ingestLoading}
              className="w-full sm:w-auto px-4 py-1.5 bg-[#238636] hover:bg-[#2ea043] border border-[rgba(240,246,252,0.1)] shadow-sm text-white font-medium rounded-md transition-colors flex items-center justify-center gap-2 text-sm disabled:opacity-50"
            >
              {ingestLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitPullRequest className="w-4 h-4" />}
              Ingest
            </button>
          </form>

          {ingestStatus && (
            <div className={`mt-4 p-3 rounded-md border flex items-center gap-2 text-sm ${ingestStatus.type === 'error' ? 'bg-[#f85149]/10 text-[#ff7b72] border-[#f85149]/40' : 'bg-[#2ea043]/10 text-[#3fb950] border-[#2ea043]/40'
              }`}>
              {ingestStatus.type === 'error' ? <AlertCircle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
              {ingestStatus.msg}
            </div>
          )}
        </section>

        {/* SECTION 2: AI SEARCH */}
        <section className="flex-1 flex flex-col">
          <div className="mb-4">
            <h2 className="text-2xl font-semibold text-[#c9d1d9]">Semantic Issue Search</h2>
            <p className="text-sm text-[#8b949e] mt-1">Ask natural language questions to find relevant bug reports.</p>
          </div>

          <form onSubmit={handleSearch} className="relative mb-6">
            <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-[#8b949e]" />
            </div>
            <input
              type="text" required
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={`Search ${selectedRepo || 'a repository'}... (e.g. "Find auth bugs")`}
              className="w-full pl-9 pr-24 py-2 rounded-md border border-[#30363d] bg-[#0d1117] focus:bg-[#0d1117] focus:ring-2 focus:ring-[#58a6ff] focus:border-[#58a6ff] outline-none text-sm transition-all shadow-sm placeholder-[#8b949e] text-[#c9d1d9]"
            />
            <div className="absolute inset-y-1 right-1">
              <button
                type="submit" disabled={searchLoading || !selectedRepo}
                className="h-full px-3 bg-[#21262d] hover:bg-[#30363d] text-[#c9d1d9] border border-[#30363d] font-medium rounded-md shadow-sm transition-colors flex items-center justify-center gap-2 text-xs disabled:opacity-50"
              >
                {searchLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
              </button>
            </div>
          </form>

          {searchStatus?.type === 'error' && (
            <div className="p-3 mb-4 rounded-md bg-[#f85149]/10 text-[#ff7b72] border border-[#f85149]/40 flex items-center gap-2 text-sm">
              <AlertCircle className="w-4 h-4" /> {searchStatus.msg}
            </div>
          )}

          {/* SEARCH RESULTS */}
          {searchResults && (
            <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <div className="flex flex-col gap-1 text-sm text-[#8b949e] mb-2">
                <div><span className="font-semibold text-[#c9d1d9]">Semantic Match:</span> "{searchResults.semantic_search_string}"</div>
                {searchResults.applied_filters?.length > 0 && (
                  <div><span className="font-semibold text-[#c9d1d9]">SQL Filter:</span> labels: {searchResults.applied_filters.join(', ')}</div>
                )}
              </div>

              {searchResults.results?.length === 0 ? (
                <div className="text-center py-10 text-[#8b949e] bg-[#161b22] rounded-md border border-[#30363d]">
                  No similar issues found. Try a different query.
                </div>
              ) : (
                <div className="grid gap-3">
                  {searchResults.results.map((issue) => (
                    <div key={issue.issue_number} className="bg-[#161b22] p-4 rounded-md border border-[#30363d] flex flex-col items-start hover:border-[#8b949e] transition-colors relative">
                      <div className="flex justify-between items-start w-full mb-2">

                        {/* THE CLICKABLE LINK WRAPPER */}
                        <h3 className="text-base font-semibold text-[#58a6ff] hover:underline leading-tight">
                          <a
                            href={`https://github.com/${selectedRepo}/issues/${issue.issue_number}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1.5"
                          >
                            {issue.title} <span className="text-[#8b949e] font-normal">#{issue.issue_number}</span>
                            <ExternalLink className="w-3.5 h-3.5 text-[#8b949e]" />
                          </a>
                        </h3>

                        <div className="flex items-center gap-1 bg-[#388bfd]/10 text-[#58a6ff] border border-[#388bfd]/30 px-2 py-0.5 rounded-full text-xs font-medium shrink-0 ml-4">
                          {issue.match_score}% Match
                        </div>
                      </div>

                      {issue.labels?.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {issue.labels.map(label => (
                            <span key={label} className="px-2 py-0.5 bg-[#388bfd]/10 text-[#58a6ff] border border-[#388bfd]/30 text-xs rounded-full font-medium">
                              {label}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}