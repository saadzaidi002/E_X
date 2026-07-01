export interface Method {
  id: string;
  name: string;
  isFast: boolean;
}

export interface Limits {
  maxFileSize: number; // bytes
  fastTierThreshold: number; // bytes
  message: string;
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
    dieharderPass?: number;
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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

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

export async function analyzeFile(file: File, methods: string[]): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('methods', JSON.stringify(methods));
  
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to analyze');
  return res.json();
}

export async function downloadBitsZip(file: File, methods: string[]): Promise<void> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('methods', JSON.stringify(methods));
  
  const res = await fetch(`${API_BASE}/api/download/bits`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to download');
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

export async function downloadPdfReport(analysisData: AnalysisResult): Promise<void> {
  const res = await fetch(`${API_BASE}/api/download/pdf`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      chartData: analysisData.chartData,
      rankedMethods: analysisData.rankedMethods,
      totalBits: analysisData.totalBits || 0,
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
