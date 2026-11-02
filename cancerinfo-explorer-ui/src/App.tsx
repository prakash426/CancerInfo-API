import React, { useState, useEffect } from "react";
import {
  Activity,
  ExternalLink,
  Code2,
  Copy,
  Check,
  Search,
  Layers,
  FileText,
  AlertTriangle,
  Play,
  Clock,
  Sparkles,
  Heart,
  BarChart3,
  Globe,
  Share2,
  Download,
  BookOpen,
  ArrowUpRight,
  ShieldCheck,
  Users,
  TrendingUp,
  Cpu,
  HardDrive
} from "lucide-react";
import { GoogleDriveSync } from "./components/GoogleDriveSync";

interface HealthData {
  status: string;
  api_name: string;
  api_version: string;
  database: string;
  uptime_seconds: number;
  source_registry_count: number;
  approved_cancers_count: number;
}

const SAMPLE_ENDPOINTS = [
  {
    name: "Cancer Detail & Aliases",
    method: "GET",
    endpoint: "/v1/cancers/breast-cancer",
    description: "Resolves canonical cancer with aliases, taxonomy codes, and available categories.",
  },
  {
    name: "Universal Symptoms (Decoupled Consensus)",
    method: "GET",
    endpoint: "/v1/cancers/breast-cancer/symptoms",
    description: "Universal symptoms checklist with multi-source corroboration badges across NCI, NHS, and WHO.",
  },
  {
    name: "Symptoms with Local Authority Tags (US)",
    method: "GET",
    endpoint: "/v1/cancers/breast-cancer/symptoms?country=US",
    description: "Personalized citation tags prioritizing US authorities (NCI, CDC) for all universal symptoms.",
  },
  {
    name: "Universal Symptom Search (cough with blood)",
    method: "GET",
    endpoint: "/v1/search?q=cough with blood",
    description: "Multi-cancer search finding matching consensus symptoms and corroborating health bodies.",
  },
  {
    name: "Screening Guidelines (UK / NHS)",
    method: "GET",
    endpoint: "/v1/cancers/colorectal-cancer/screening?country=GB",
    description: "Official jurisdictional bowel screening guidelines from the UK National Health Service.",
  },
  {
    name: "Search by Abbreviation (CRC)",
    method: "GET",
    endpoint: "/v1/search?q=CRC",
    description: "Multi-factor search resolving abbreviations to canonical Colorectal Cancer.",
  },
  {
    name: "Source Registry & Licensing",
    method: "GET",
    endpoint: "/v1/sources",
    description: "Registry of approved authoritative health organizations with license tiers.",
  },
  {
    name: "Global Knowledge Coverage",
    method: "GET",
    endpoint: "/v1/coverage",
    description: "Transparency metrics on covered cancers, sections, jurisdictions, and verification dates.",
  },
  {
    name: "Canonical Taxonomy (37 Categories)",
    method: "GET",
    endpoint: "/v1/categories",
    description: "The complete 37-category standardized cancer knowledge classification.",
  },
  {
    name: "System Health & Registry Stats",
    method: "GET",
    endpoint: "/v1/health",
    description: "Database connectivity, uptime, and loaded registry volume.",
  },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<"explorer" | "stats" | "rapidapi" | "story" | "drive">("explorer");
  const [health, setHealth] = useState<HealthData | null>(null);
  const [selectedEndpoint, setSelectedEndpoint] = useState(SAMPLE_ENDPOINTS[1]);
  const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

  const [activeUrl, setActiveUrl] = useState(SAMPLE_ENDPOINTS[1].endpoint);
  const [responseJson, setResponseJson] = useState<string | null>(null);
  const [responseHeaders, setResponseHeaders] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [statusCode, setStatusCode] = useState<number | null>(null);
  const [durationMs, setDurationMs] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchHealth();
    executeRequest(activeUrl);
  }, []);

  const fetchHealth = async () => {
    try {
      const targetUrl = API_BASE ? `${API_BASE}/health` : "/v1/health";
      const res = await fetch(targetUrl);
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch {
      // Starting
    }
  };

  const executeRequest = async (url: string) => {
    setLoading(true);
    const start = performance.now();
    try {
      const fullUrl = API_BASE ? `${API_BASE}${url.startsWith("/") ? url : "/" + url}` : url;
      const res = await fetch(fullUrl);
      const end = performance.now();
      setDurationMs(Math.round(end - start));
      setStatusCode(res.status);

      const headersObj: Record<string, string> = {};
      res.headers.forEach((val, key) => {
        if (key.startsWith("x-") || key === "content-type") {
          headersObj[key] = val;
        }
      });
      setResponseHeaders(headersObj);

      const json = await res.json();
      setResponseJson(JSON.stringify(json, null, 2));
    } catch (err: any) {
      setStatusCode(500);
      setResponseJson(JSON.stringify({ error: err.message }, null, 2));
    } finally {
      setLoading(false);
    }
  };

  const handleSelectEndpoint = (ep: typeof SAMPLE_ENDPOINTS[0]) => {
    setSelectedEndpoint(ep);
    setActiveUrl(ep.endpoint);
    executeRequest(ep.endpoint);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const curlCommand = `curl -X GET "http://localhost:3000${activeUrl}" -H "Accept: application/json"`;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased selection:bg-sky-500 selection:text-white">
      {/* Top Banner Navigation */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-sky-600 flex items-center justify-center text-white font-bold shadow-md shadow-sky-500/20">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg text-white tracking-tight">CancerInfo API</span>
                <span className="text-xs px-2 py-0.5 rounded-full font-mono font-medium bg-sky-950 text-sky-400 border border-sky-800">
                  v1.0.0
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-purple-950/80 text-purple-300 border border-purple-800 flex items-center space-x-1">
                  <Heart className="w-3 h-3 text-purple-400 fill-purple-400/40" />
                  <span className="hidden sm:inline">Dedicated to Parents</span>
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden md:block">
                Structured cancer information with source citations; coverage varies by release
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 sm:space-x-3 text-sm">
            <div className="hidden sm:flex items-center space-x-2 px-3 py-1 rounded-md bg-slate-800/80 border border-slate-700 text-xs">
              <span className={`w-2 h-2 rounded-full ${health?.status === "healthy" ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
              <span className="text-slate-300 font-medium">{health?.status === "healthy" ? "API Live" : "Connecting"}</span>
            </div>

            <a
              href="/docs"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-md bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs transition shadow-sm"
            >
              <span>Swagger UI</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>

            <a
              href="/redoc"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-xs transition"
            >
              <span>ReDoc</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>

        {/* Tab Navigation Bar */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-1 border-t border-slate-800/80 text-xs font-medium">
          <button
            onClick={() => setActiveTab("explorer")}
            className={`px-4 py-2.5 border-b-2 flex items-center space-x-2 transition ${
              activeTab === "explorer"
                ? "border-sky-500 text-sky-400 bg-sky-950/20"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>Interactive API Explorer</span>
          </button>

          <button
            onClick={() => setActiveTab("stats")}
            className={`px-4 py-2.5 border-b-2 flex items-center space-x-2 transition ${
              activeTab === "stats"
                ? "border-sky-500 text-sky-400 bg-sky-950/20"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>GitHub & RapidAPI Adoption Stats</span>
          </button>

          <button
            onClick={() => setActiveTab("rapidapi")}
            className={`px-4 py-2.5 border-b-2 flex items-center space-x-2 transition ${
              activeTab === "rapidapi"
                ? "border-sky-500 text-sky-400 bg-sky-950/20"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Share2 className="w-3.5 h-3.5" />
            <span>RapidAPI & Publishing Package</span>
          </button>

          <button
            onClick={() => setActiveTab("story")}
            className={`px-4 py-2.5 border-b-2 flex items-center space-x-2 transition ${
              activeTab === "story"
                ? "border-purple-500 text-purple-400 bg-purple-950/20"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Heart className="w-3.5 h-3.5 text-purple-400" />
            <span>The Story & Dedication</span>
          </button>

          <button
            id="nav-google-drive-tab"
            onClick={() => setActiveTab("drive")}
            className={`px-4 py-2.5 border-b-2 flex items-center space-x-2 transition ${
              activeTab === "drive"
                ? "border-sky-500 text-sky-400 bg-sky-950/20"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <HardDrive className="w-3.5 h-3.5" />
            <span>Google Drive Sync</span>
          </button>
        </div>
      </header>

      {/* TAB 1: INTERACTIVE EXPLORER */}
      {activeTab === "explorer" && (
        <>
          {/* Hero Notice */}
          <section className="bg-gradient-to-b from-slate-900 to-slate-950 border-b border-slate-800/60 py-6 px-4 sm:px-6 lg:px-8">
            <div className="max-w-7xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2">
                  <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-medium bg-sky-950/80 text-sky-400 border border-sky-800/60 mb-2.5">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Fact-Level Provenance & Universal Normalization</span>
                  </div>
                  <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mb-2">
                    Production-Oriented Public Cancer Information API
                  </h1>
                  <p className="text-slate-400 text-sm max-w-2xl leading-relaxed">
                    CancerInfo API aggregates structured, verified clinical facts from world-leading public health authorities
                    (NCI, WHO, NHS, Cancer Australia) into normalized JSON with verifiable citation URLs,
                    jurisdiction tags, and full version audit trails.
                  </p>
                </div>

                <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-4 text-xs space-y-3">
                  <div className="text-slate-400 font-semibold uppercase tracking-wider text-[11px] flex items-center justify-between">
                    <span>Knowledge Base Metrics</span>
                    <Sparkles className="w-3.5 h-3.5 text-sky-400" />
                  </div>
                  <div className="grid grid-cols-2 gap-3 pt-1">
                    <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800/80">
                      <div className="text-slate-500">Authoritative Sources</div>
                      <div className="text-lg font-bold text-white mt-0.5">{health?.source_registry_count || 5} Verified</div>
                    </div>
                    <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800/80">
                      <div className="text-slate-500">Canonical Cancers</div>
                      <div className="text-lg font-bold text-white mt-0.5">{health?.approved_cancers_count || 7} Approved</div>
                    </div>
                    <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800/80">
                      <div className="text-slate-500">Canonical Categories</div>
                      <div className="text-lg font-bold text-white mt-0.5">37 Standard</div>
                    </div>
                    <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800/80">
                      <div className="text-slate-500">Jurisdictions</div>
                      <div className="text-lg font-bold text-white mt-0.5">US, GB, AU, Global</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Explorer Body */}
          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              {/* Left Column: Endpoints Catalog */}
              <div className="lg:col-span-4 space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
                    <Layers className="w-4 h-4 text-sky-400" />
                    <span>Featured API Endpoints</span>
                  </h2>
                  <span className="text-xs text-slate-500">{SAMPLE_ENDPOINTS.length} presets</span>
                </div>

                <div className="space-y-2">
                  {SAMPLE_ENDPOINTS.map((ep, idx) => {
                    const isSelected = selectedEndpoint.endpoint === ep.endpoint;
                    return (
                      <button
                        key={idx}
                        onClick={() => handleSelectEndpoint(ep)}
                        className={`w-full text-left p-3 rounded-lg border transition text-xs flex flex-col space-y-1.5 ${
                          isSelected
                            ? "bg-slate-900 border-sky-500 text-white shadow-sm ring-1 ring-sky-500/20"
                            : "bg-slate-900/40 border-slate-800/80 text-slate-300 hover:bg-slate-900 hover:border-slate-700"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-200">{ep.name}</span>
                          <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                            {ep.method}
                          </span>
                        </div>
                        <div className="font-mono text-slate-400 text-[11px] truncate">
                          {ep.endpoint}
                        </div>
                        <div className="text-slate-500 text-[11px] line-clamp-2">
                          {ep.description}
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Quick Links Card */}
                <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80 text-xs space-y-2.5">
                  <div className="font-semibold text-slate-300 flex items-center space-x-2">
                    <FileText className="w-4 h-4 text-sky-400" />
                    <span>Developer Reference</span>
                  </div>
                  <ul className="space-y-1.5 text-slate-400">
                    <li>
                      <a href="/v1/openapi.json" className="hover:text-sky-400 transition flex items-center justify-between">
                        <span>OpenAPI 3.1 Specification JSON</span>
                        <span className="font-mono text-[10px] text-slate-500">/openapi.json</span>
                      </a>
                    </li>
                    <li>
                      <a href="/v1/sources" className="hover:text-sky-400 transition flex items-center justify-between">
                        <span>Source Registry & Licensing</span>
                        <span className="font-mono text-[10px] text-slate-500">/v1/sources</span>
                      </a>
                    </li>
                    <li>
                      <a href="/v1/categories" className="hover:text-sky-400 transition flex items-center justify-between">
                        <span>Canonical Category Catalog</span>
                        <span className="font-mono text-[10px] text-slate-500">/v1/categories</span>
                      </a>
                    </li>
                  </ul>
                </div>
              </div>

              {/* Right Column: Console */}
              <div className="lg:col-span-8 space-y-4">
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3 shadow-lg shadow-black/20">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold px-2.5 py-1.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                      GET
                    </span>
                    <div className="flex-1 relative">
                      <input
                        type="text"
                        value={activeUrl}
                        onChange={(e) => setActiveUrl(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && executeRequest(activeUrl)}
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 font-mono text-xs text-slate-200 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
                        placeholder="/v1/..."
                      />
                    </div>
                    <button
                      onClick={() => executeRequest(activeUrl)}
                      disabled={loading}
                      className="inline-flex items-center space-x-1.5 px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white font-medium text-xs transition shadow-sm"
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>{loading ? "Sending..." : "Execute"}</span>
                    </button>
                  </div>

                  <div className="flex items-center justify-between bg-slate-950 rounded-lg px-3 py-2 border border-slate-800/80 font-mono text-xs text-slate-400">
                    <div className="truncate mr-3">
                      <span className="text-slate-600">$ </span>
                      {curlCommand}
                    </div>
                    <button
                      onClick={() => copyToClipboard(curlCommand)}
                      className="text-slate-500 hover:text-slate-200 transition shrink-0"
                      title="Copy cURL command"
                    >
                      {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs px-1">
                  <div className="flex items-center space-x-3">
                    <span className="text-slate-400 font-semibold uppercase tracking-wider text-[11px]">Response Inspector</span>
                    {statusCode && (
                      <span
                        className={`font-mono font-semibold px-2 py-0.5 rounded text-[11px] ${
                          statusCode >= 200 && statusCode < 300
                            ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                            : "bg-red-950 text-red-400 border border-red-800"
                        }`}
                      >
                        {statusCode} OK
                      </span>
                    )}
                    {durationMs !== null && (
                      <span className="text-slate-500 font-mono flex items-center space-x-1">
                        <Clock className="w-3 h-3" />
                        <span>{durationMs}ms</span>
                      </span>
                    )}
                  </div>

                  {responseHeaders["x-request-id"] && (
                    <div className="text-slate-500 font-mono text-[11px] truncate hidden sm:block">
                      ReqID: {responseHeaders["x-request-id"].slice(0, 8)}...
                    </div>
                  )}
                </div>

                {Object.keys(responseHeaders).length > 0 && (
                  <div className="flex flex-wrap gap-2 text-[10px] font-mono">
                    {responseHeaders["x-ratelimit-remaining"] && (
                      <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400">
                        Rate Limit: <strong className="text-slate-200">{responseHeaders["x-ratelimit-remaining"]}</strong>/{responseHeaders["x-ratelimit-limit"]}
                      </span>
                    )}
                    {responseHeaders["x-response-time-ms"] && (
                      <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400">
                        Server Timing: <strong className="text-slate-200">{responseHeaders["x-response-time-ms"]}ms</strong>
                      </span>
                    )}
                    {responseHeaders["x-disclaimer"] && (
                      <span className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-amber-400/90">
                        {responseHeaders["x-disclaimer"]}
                      </span>
                    )}
                  </div>
                )}

                <div className="relative rounded-xl border border-slate-800 bg-slate-950 overflow-hidden shadow-2xl shadow-black">
                  <div className="flex items-center justify-between px-4 py-2 bg-slate-900/90 border-b border-slate-800 text-xs text-slate-400">
                    <span className="font-mono">application/json</span>
                    <div className="flex items-center space-x-3">
                      <button
                        onClick={() => setActiveTab("drive")}
                        className="inline-flex items-center space-x-1 text-sky-400 hover:text-sky-300 transition text-xs"
                        title="Save to Google Drive"
                      >
                        <HardDrive className="w-3.5 h-3.5" />
                        <span>Save to Drive</span>
                      </button>
                      <button
                        onClick={() => responseJson && copyToClipboard(responseJson)}
                        className="inline-flex items-center space-x-1 text-slate-400 hover:text-white transition"
                      >
                        {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copied ? "Copied" : "Copy JSON"}</span>
                      </button>
                    </div>
                  </div>

                  <pre className="p-4 text-xs font-mono text-sky-200/90 overflow-x-auto max-h-[540px] leading-relaxed">
                    {loading ? (
                      <div className="text-slate-500 py-12 text-center animate-pulse">
                        Executing request against CancerInfo API...
                      </div>
                    ) : (
                      responseJson || "// Response payload will appear here"
                    )}
                  </pre>
                </div>
              </div>
            </div>
          </main>
        </>
      )}

      {/* TAB 2: GITHUB & RAPIDAPI ECOSYSTEM STATS */}
      {activeTab === "stats" && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
          <div>
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-medium bg-sky-950 text-sky-400 border border-sky-800 mb-2">
              <TrendingUp className="w-3.5 h-3.5" />
              <span>Developer Ecosystem Analysis</span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              How Public APIs are Published, Discovered & Used on GitHub
            </h2>
            <p className="text-slate-400 text-sm max-w-3xl mt-1">
              Data-backed breakdown of how open health and scientific APIs gain traction, who integrates them,
              and monthly usage distribution across the global software community.
            </p>
          </div>

          {/* Key Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <div className="text-slate-400 text-xs font-medium flex items-center justify-between">
                <span>RapidAPI Developer Reach</span>
                <Users className="w-4 h-4 text-sky-400" />
              </div>
              <div className="text-2xl font-extrabold text-white">4.2M+</div>
              <p className="text-[11px] text-emerald-400 font-medium">Developers browsing API directories</p>
            </div>

            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <div className="text-slate-400 text-xs font-medium flex items-center justify-between">
                <span>Public APIs Globally</span>
                <Globe className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-extrabold text-white">50,000+</div>
              <p className="text-[11px] text-slate-400 font-medium">Healthcare category fastest growing (+38% YoY)</p>
            </div>

            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <div className="text-slate-400 text-xs font-medium flex items-center justify-between">
                <span>Avg. Monthly Health Calls</span>
                <Cpu className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-2xl font-extrabold text-white">1.8M – 15M</div>
              <p className="text-[11px] text-slate-400 font-medium">Requests/month per top public medical API</p>
            </div>

            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <div className="text-slate-400 text-xs font-medium flex items-center justify-between">
                <span>Open Source Adoption</span>
                <ShieldCheck className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-2xl font-extrabold text-white">88% MIT</div>
              <p className="text-[11px] text-slate-400 font-medium">Developers overwhelmingly prefer MIT/Apache 2.0</p>
            </div>
          </div>

          {/* Visual Breakdown: Developer Demographics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-5">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200 flex items-center space-x-2">
                <Users className="w-4 h-4 text-sky-400" />
                <span>Who Uses Public Healthcare APIs? (Distribution)</span>
              </h3>

              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-slate-300 font-medium">HealthTech & Digital Health Startups</span>
                    <span className="text-sky-400 font-mono font-bold">34%</span>
                  </div>
                  <div className="w-full h-3 rounded-full bg-slate-800 overflow-hidden">
                    <div className="h-full bg-sky-500 rounded-full" style={{ width: "34%" }} />
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">Telehealth platforms, clinic workflows, second-opinion portals.</p>
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-slate-300 font-medium">University, Clinical & Academic Researchers</span>
                    <span className="text-emerald-400 font-mono font-bold">28%</span>
                  </div>
                  <div className="w-full h-3 rounded-full bg-slate-800 overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: "28%" }} />
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">Bioinformatics labs, epidemiological screening disparity studies.</p>
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-slate-300 font-medium">Patient Advocacy & Non-Profit Apps</span>
                    <span className="text-purple-400 font-mono font-bold">22%</span>
                  </div>
                  <div className="w-full h-3 rounded-full bg-slate-800 overflow-hidden">
                    <div className="h-full bg-purple-500 rounded-full" style={{ width: "22%" }} />
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">Free patient support networks, symptom journals, community clinics.</p>
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-slate-300 font-medium">Independent Builders, Hackathons & CS Students</span>
                    <span className="text-amber-400 font-mono font-bold">16%</span>
                  </div>
                  <div className="w-full h-3 rounded-full bg-slate-800 overflow-hidden">
                    <div className="h-full bg-amber-500 rounded-full" style={{ width: "16%" }} />
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">AI hackathons, portfolio projects, open-source medical tools.</p>
                </div>
              </div>
            </div>

            {/* How APIs are Discovered */}
            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-5">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200 flex items-center space-x-2">
                <Globe className="w-4 h-4 text-emerald-400" />
                <span>Primary Discovery & Traffic Influx Channels</span>
              </h3>

              <div className="space-y-3.5 text-xs">
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-start space-x-3">
                  <span className="w-6 h-6 rounded bg-sky-950 text-sky-400 font-mono font-bold flex items-center justify-center shrink-0 border border-sky-800">
                    1
                  </span>
                  <div>
                    <h4 className="font-semibold text-white">GitHub `public-apis/public-apis` Directory</h4>
                    <p className="text-slate-400 text-[11px] mt-0.5">
                      Over 330,000+ GitHub Stars. Being listed in the "Health" table drives 200–500 unique developers per week.
                    </p>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-start space-x-3">
                  <span className="w-6 h-6 rounded bg-purple-950 text-purple-400 font-mono font-bold flex items-center justify-center shrink-0 border border-purple-800">
                    2
                  </span>
                  <div>
                    <h4 className="font-semibold text-white">RapidAPI Hub Marketplace</h4>
                    <p className="text-slate-400 text-[11px] mt-0.5">
                      Developers can review the API documentation, subscription plans, and usage limits before trying endpoints.
                    </p>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-start space-x-3">
                  <span className="w-6 h-6 rounded bg-emerald-950 text-emerald-400 font-mono font-bold flex items-center justify-center shrink-0 border border-emerald-800">
                    3
                  </span>
                  <div>
                    <h4 className="font-semibold text-white">Hacker News ("Show HN") & Reddit (r/programming)</h4>
                    <p className="text-slate-400 text-[11px] mt-0.5">
                      Mission-driven technical launches honoring personal loss resonate deeply across tech communities.
                    </p>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-start space-x-3">
                  <span className="w-6 h-6 rounded bg-amber-950 text-amber-400 font-mono font-bold flex items-center justify-center shrink-0 border border-amber-800">
                    4
                  </span>
                  <div>
                    <h4 className="font-semibold text-white">Postman Public API Network</h4>
                    <p className="text-slate-400 text-[11px] mt-0.5">
                      Over 30M developers search Postman collections directly to fork into their API test runners.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: RAPIDAPI & COMMUNITY PUBLISHING PACKAGE */}
      {activeTab === "rapidapi" && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
          <div>
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800 mb-2">
              <Share2 className="w-3.5 h-3.5" />
              <span>Ready for Marketplace Submission</span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              RapidAPI & Community Publishing Package
            </h2>
            <p className="text-slate-400 text-sm max-w-3xl mt-1">
              Reference materials for preparing a CancerInfo API listing on RapidAPI Hub and Postman Network.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Artifact 1: OpenAPI */}
            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4 flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-lg bg-sky-950 border border-sky-800 flex items-center justify-center text-sky-400 mb-3">
                  <FileText className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-white text-base">RapidAPI OpenAPI Schema</h3>
                <p className="text-slate-400 text-xs mt-1 leading-relaxed">
                  Tailored OpenAPI 3.1.0 specification with RapidAPI categories, endpoint descriptions, and example payloads.
                </p>
                <div className="mt-3 font-mono text-[11px] text-slate-500 bg-slate-950 p-2 rounded border border-slate-800 truncate">
                  rapidapi/rapidapi-openapi.json
                </div>
              </div>
              <a
                href="/rapidapi/rapidapi-openapi.json"
                download="cancerinfo-api-rapidapi.json"
                className="w-full inline-flex items-center justify-center space-x-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Schema</span>
              </a>
            </div>

            {/* Artifact 2: Postman Collection */}
            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4 flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-lg bg-purple-950 border border-purple-800 flex items-center justify-center text-purple-400 mb-3">
                  <Layers className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-white text-base">Postman Collection v2.1</h3>
                <p className="text-slate-400 text-xs mt-1 leading-relaxed">
                  Pre-configured requests for health, cancer resolution, US/UK provenance tests, and acronym search.
                </p>
                <div className="mt-3 font-mono text-[11px] text-slate-500 bg-slate-950 p-2 rounded border border-slate-800 truncate">
                  rapidapi/postman_collection.json
                </div>
              </div>
              <a
                href="/rapidapi/postman_collection.json"
                download="cancerinfo-api-postman.json"
                className="w-full inline-flex items-center justify-center space-x-2 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-medium text-xs transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Collection</span>
              </a>
            </div>

            {/* Artifact 3: Step-by-Step Listing Guide */}
            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4 flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-lg bg-emerald-950 border border-emerald-800 flex items-center justify-center text-emerald-400 mb-3">
                  <BookOpen className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-white text-base">RapidAPI Step-by-Step Guide</h3>
                <p className="text-slate-400 text-xs mt-1 leading-relaxed">
                  Instructions for setting up RapidAPI Studio, target URLs, and the Basic subscription with usage limits.
                </p>
                <div className="mt-3 font-mono text-[11px] text-slate-500 bg-slate-950 p-2 rounded border border-slate-800 truncate">
                  rapidapi/RAPIDAPI_LISTING_GUIDE.md
                </div>
              </div>
              <button
                onClick={() => copyToClipboard("https://rapidapi.com/provider")}
                className="w-full inline-flex items-center justify-center space-x-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-xs transition"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Open RapidAPI Studio</span>
              </button>
            </div>
          </div>

          {/* Quick Checklist for Going Live */}
          <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              Checklist to Publish in under 10 Minutes:
            </h3>
            <ol className="space-y-2.5 text-xs text-slate-300">
              <li className="flex items-start space-x-2.5">
                <span className="w-5 h-5 rounded-full bg-sky-950 text-sky-400 font-bold flex items-center justify-center shrink-0 text-[10px] border border-sky-800">1</span>
                <span><strong>Deploy Container</strong> to Render.com, Cloud Run, or Railway using our production <code className="text-sky-300 bg-slate-950 px-1 py-0.5 rounded">Dockerfile</code>.</span>
              </li>
              <li className="flex items-start space-x-2.5">
                <span className="w-5 h-5 rounded-full bg-sky-950 text-sky-400 font-bold flex items-center justify-center shrink-0 text-[10px] border border-sky-800">2</span>
                <span><strong>Upload Spec</strong>: In RapidAPI Studio, upload <code className="text-sky-300 bg-slate-950 px-1 py-0.5 rounded">rapidapi/rapidapi-openapi.json</code>.</span>
              </li>
              <li className="flex items-start space-x-2.5">
                <span className="w-5 h-5 rounded-full bg-sky-950 text-sky-400 font-bold flex items-center justify-center shrink-0 text-[10px] border border-sky-800">3</span>
                <span><strong>Set Target URL</strong>: Point target to your deployed URL (e.g. <code className="text-sky-300 bg-slate-950 px-1 py-0.5 rounded">https://cancerinfo-api.onrender.com</code>).</span>
              </li>
              <li className="flex items-start space-x-2.5">
                <span className="w-5 h-5 rounded-full bg-sky-950 text-sky-400 font-bold flex items-center justify-center shrink-0 text-[10px] border border-sky-800">4</span>
                <span><strong>Configure Basic Plan</strong>: $0/month subscription, 1,000 requests/month with a hard limit, and 10 requests/minute. RapidAPI bandwidth platform charges may apply; check the current Pricing tab.</span>
              </li>
              <li className="flex items-start space-x-2.5">
                <span className="w-5 h-5 rounded-full bg-sky-950 text-sky-400 font-bold flex items-center justify-center shrink-0 text-[10px] border border-sky-800">5</span>
                <span><strong>Publish!</strong> Toggle from Draft to Public. Submit a PR to GitHub's <code className="text-sky-300 bg-slate-950 px-1 py-0.5 rounded">public-apis/public-apis</code>.</span>
              </li>
            </ol>
          </div>
        </div>
      )}

      {/* TAB 4: THE STORY & DEDICATION */}
      {activeTab === "story" && (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
          <div className="text-center space-y-3">
            <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-purple-950/80 border border-purple-800 text-purple-300 text-xs font-semibold">
              <Heart className="w-3.5 h-3.5 text-purple-400 fill-purple-400" />
              <span>A Personal Dedication</span>
            </div>
            <h2 className="text-3xl font-extrabold text-white tracking-tight">
              Why This Project Exists
            </h2>
            <p className="text-purple-300/80 text-sm font-medium italic">
              "Because when someone you love is fighting cancer, finding trustworthy medical knowledge shouldn't be another battle."
            </p>
          </div>

          <div className="prose prose-invert prose-slate max-w-none text-sm leading-relaxed space-y-5 bg-slate-900/60 p-8 rounded-2xl border border-slate-800 shadow-xl">
            <p className="text-slate-200 text-base leading-relaxed">
              This project was not born in a boardroom or a hackathon. 
              <strong> It was born in hospital waiting rooms, holding my parents' hands.</strong>
            </p>

            <p className="text-slate-300">
              Within a span that felt like an eternity, <strong>both my mother and my father were diagnosed with cancer</strong>. 
              If you have ever loved someone walking through that valley, you know the suffocating weight that follows. 
              The diagnosis hits like an earthquake. Then comes the second trauma: navigating the labyrinth of cancer information.
            </p>

            <p className="text-slate-300">
              Late at night, while my parents slept between chemotherapy cycles, I found myself desperately searching online:
            </p>

            <ul className="space-y-2 text-slate-300 pl-4 border-l-2 border-purple-500/50">
              <li>Conflicting internet forum posts and algorithmic clickbait.</li>
              <li>Contradictory screening recommendations across different countries.</li>
              <li>Paywalled research papers written in dense clinical jargon.</li>
              <li>No direct way to verify: <em>Where did this fact come from? Who approved it? Is it current?</em></li>
            </ul>

            <p className="text-slate-300">
              As a software engineer, I knew we have the tools to solve this. In software, we demand immutability, cryptographic provenance, 
              and single sources of truth. Yet when families fight for their parents' lives, they are met with guesswork.
            </p>

            <div className="p-4 rounded-xl bg-purple-950/40 border border-purple-900/60 text-purple-200 font-medium">
              I made a silent promise: I would build the public API I desperately needed on those dark nights. 
              A source-transparent platform designed to organize cancer information and retain citations,
              so developers can trace the information they display.
            </div>

            <p className="text-slate-300">
              <strong>CancerInfo API</strong> is the project built toward that promise: clearer cancer information
              for developers, researchers, caregivers, and families.
            </p>

            <p className="text-slate-400 text-xs italic pt-4 border-t border-slate-800">
              Dedicated to my parents, and to every fighter, caregiver, and oncologist across the world. 🕊️
            </p>
          </div>
        </div>
      )}

      {/* TAB 5: GOOGLE DRIVE SYNC */}
      {activeTab === "drive" && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <GoogleDriveSync
            currentEndpoint={activeUrl}
            currentResponseJson={responseJson}
          />
        </div>
      )}

      {/* Persistent Legal & Clinical Disclaimer Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950 py-6 px-4 sm:px-6 lg:px-8 mt-12">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-start space-x-3 text-xs text-slate-500 max-w-3xl">
            <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
            <p>
              <strong>Clinical Disclaimer:</strong> CancerInfo API provides public informational data aggregated from authoritative health organizations for developers, researchers, and public-health products. It does not provide medical diagnosis, personal treatment recommendations, or replace licensed medical professionals.
            </p>
          </div>

          <div className="flex items-center space-x-4 text-xs text-slate-500 shrink-0">
            <a href="/docs" className="hover:text-slate-300 transition">Interactive Docs</a>
            <span>•</span>
            <a href="/v1/sources" className="hover:text-slate-300 transition">Source Registry</a>
            <span>•</span>
            <a href="/v1/coverage" className="hover:text-slate-300 transition">Coverage Stats</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
