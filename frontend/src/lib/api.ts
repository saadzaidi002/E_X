export interface Method {
  id: string;
  name: string;
  isFast: boolean;
}

export interface Limits {
  maxFileSize: number; // bytes
  fastTierThreshold: number; // bytes
  message: string;
  exportBinaryBytes?: number; // bytes of a binary file the bitstream export uses
  exportTextBytes?: number; // same, for ASCII '0'/'1' text files
}

export interface ChartData {
  method: string;
  shannonEntropy: number;
  minEntropy: number;
  bitRate: number;
  bias: number;
  executionTime: number;
  passCount: number;
  failCount: number;
  invalidCount?: number;
  totalCount?: number;
  details?: any[];
  compression?: any;
  testu01?: any;
  dieharder?: any;
}

export interface AnalysisResult {
  id: string;
  bestMethod: string;
  bestMethodExplanation: string;
  totalBits: number;
  fileSizeBytes?: number | null;
  chartData: ChartData[];
  rankedMethods: {
    method: string;
    score: number;
    nistPass: number;
    shannon: number;
    minEntropy: number;
    bias: number;
    bitRate: number;
    compressionPass?: number;
    testu01Pass?: number;
    testu01Total?: number;
    dieharderPass?: number;
    dieharderTotal?: number;
  }[];
}

const mockMethods: Method[] = [
  { id: 'm1', name: 'Von Neumann', isFast: true },
  { id: 'm2', name: 'Toeplitz Hashing', isFast: true },
  { id: 'm3', name: 'Trevisan', isFast: false },
  { id: 'm4', name: 'SHA-256', isFast: true },
  { id: 'm5', name: 'AES-CBC-MAC', isFast: false },
  { id: 'm6', name: 'LFSR', isFast: true },
  { id: 'm7', name: 'Chacha20', isFast: true },
  { id: 'm8', name: 'XOR-Shift', isFast: true },
  { id: 'm9', name: 'Bilinear', isFast: false },
  { id: 'm10', name: 'Sponge Construction', isFast: true },
  { id: 'm11', name: 'Blum Blum Shub', isFast: false },
  { id: 'm12', name: 'Multi-Bit Extraction', isFast: true },
  { id: 'm13', name: 'Markov Chain', isFast: true },
  { id: 'm14', name: 'Elias Gamma', isFast: true },
  { id: 'm15', name: 'Matrix Rank', isFast: false },
  { id: 'm16', name: 'Linear Congruential', isFast: true },
  { id: 'm17', name: 'Hash-based KDF', isFast: true },
  { id: 'm18', name: 'HMAC-SHA256', isFast: true },
  { id: 'm19', name: 'Poly1305', isFast: true },
  { id: 'm20', name: 'SipHash', isFast: true },
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function getMethods(): Promise<Method[]> {
  const res = await fetch(`${API_BASE}/api/methods`);
  if (!res.ok) throw new Error('Failed to fetch methods');
  return res.json();
}

export async function getLimits(): Promise<Limits> {
  const res = await fetch(`${API_BASE}/api/limits`);
  if (!res.ok) throw new Error('Failed to fetch limits');
  return res.json();
}

export interface UploadProgress {
  loaded: number; // bytes sent so far
  total: number; // bytes to send
}

// fetch() cannot report upload progress, so the upload goes through XMLHttpRequest.
function postWithUploadProgress(
  url: string,
  body: FormData,
  onUploadProgress?: (p: UploadProgress) => void
): Promise<{ ok: boolean; status: number; text: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url);
    if (onUploadProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onUploadProgress({ loaded: e.loaded, total: e.total });
      };
    }
    xhr.onload = () => resolve({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status, text: xhr.responseText });
    xhr.onerror = () => reject(new Error('Upload failed: could not reach the analysis server.'));
    xhr.onabort = () => reject(new Error('Upload was cancelled.'));
    xhr.send(body);
  });
}

export async function analyzeFile(
  file: File,
  methods: string[],
  tests: string[],
  onProgress?: (logs: string[]) => void,
  onUploadProgress?: (p: UploadProgress) => void
): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('methods', JSON.stringify(methods));
  formData.append('tests', JSON.stringify(tests));

  const startRes = await postWithUploadProgress(`${API_BASE}/api/analyze/start`, formData, onUploadProgress);
  if (!startRes.ok) throw new Error(`Failed to start analysis job (${startRes.status})`);
  const { job_id } = JSON.parse(startRes.text);

  // Jobs live in the server's memory. A 404 for a job that was just running means
  // the server restarted (e.g. a new version was deployed) and the job is gone.
  // Network errors and 5xx responses are what a restart looks like while it is in
  // progress, so those are retried for a while before giving up.
  const MAX_UNREACHABLE_MS = 3 * 60 * 1000;
  let unreachableSince: number | null = null;

  while (true) {
    let statusRes: Response | null = null;
    try {
      statusRes = await fetch(`${API_BASE}/api/analyze/status/${job_id}`);
    } catch {
      statusRes = null;
    }

    if (statusRes && statusRes.status === 404) {
      throw new Error('The analysis server restarted and this analysis was lost. Your file and selections are still here: click Execute Pipeline to run it again.');
    }

    if (!statusRes || !statusRes.ok) {
      unreachableSince ??= Date.now();
      if (Date.now() - unreachableSince > MAX_UNREACHABLE_MS) {
        throw new Error('Lost connection to the analysis server for over 3 minutes. Check your internet connection, then click Execute Pipeline to run the analysis again.');
      }
      await new Promise(r => setTimeout(r, 3000));
      continue;
    }
    unreachableSince = null;

    const statusData = await statusRes.json();
    
    if (onProgress && statusData.logs) {
      onProgress(statusData.logs);
    }
    
    if (statusData.status === 'complete') {
      return statusData.result;
    }
    
    if (statusData.status === 'error') {
      throw new Error(statusData.error || 'Unknown analysis error occurred');
    }
    
    // Poll every 1.5 seconds
    await new Promise(r => setTimeout(r, 1500));
  }
}

// The export covers the analysis window at the start of the file, so only that
// part is uploaded. Sending a whole 500 MB file again took minutes for nothing.
async function exportSlice(file: File): Promise<Blob> {
  const limits = await getLimits();
  if (!limits.exportBinaryBytes || !limits.exportTextBytes) return file;
  const head = new Uint8Array(await file.slice(0, 4096).arrayBuffer());
  const isBit = (b: number) => b === 48 || b === 49;
  const isText = head.length > 0 && head.some(isBit) &&
    head.every(b => isBit(b) || b === 32 || b === 9 || b === 13 || b === 10 || b === 44);
  return file.slice(0, isText ? limits.exportTextBytes : limits.exportBinaryBytes);
}

export async function downloadBitsZip(file: File, methods: string[]): Promise<void> {
  const formData = new FormData();
  formData.append('file', await exportSlice(file), file.name);
  formData.append('methods', JSON.stringify(methods));

  const res = await fetch(`${API_BASE}/api/download/bits`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    let errorMsg = 'Failed to export bitstreams';
    try {
      errorMsg += ` - ${res.status}: ${(await res.text()).substring(0, 100)}`;
    } catch (e) {}
    throw new Error(errorMsg);
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = "extracted_bits.zip";
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export async function downloadPdfReport(analysisData: AnalysisResult, selectedTests: Set<string>): Promise<void> {
  const res = await fetch(`${API_BASE}/api/download/pdf`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      chartData: analysisData.chartData,
      rankedMethods: analysisData.rankedMethods,
      totalBits: analysisData.totalBits || 0,
      fileSizeBytes: analysisData.fileSizeBytes ?? null,
      selectedTests: Array.from(selectedTests),
    }),
  });
  if (!res.ok) {
    let errorMsg = 'Failed to download';
    try {
      const errorText = await res.text();
      errorMsg += ` - ${res.status}: ${errorText.substring(0, 100)}`;
    } catch (e) {}
    throw new Error(errorMsg);
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = "RNG_Report.pdf";
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}
