export type ReviewTarget = "album" | "artist";
export type ReviewMode = "create" | "translate" | "improve";

export interface ProviderInfo {
  name: string;
  configured: boolean;
  available?: boolean | null;
  model?: string | null;
  details: Record<string, unknown>;
}

export interface ConfigurationResponse {
  configuration: Configuration;
}

export interface Configuration {
  plexConfigured: boolean;
  plexUrl?: string | null;
  plexTokenConfigured?: boolean;
  plexTokenMasked?: string | null;
  aiProvider: string;
  aiModel: string;
  openaiApiKeyConfigured: boolean;
  openaiApiKeyMasked?: string | null;
  discogsConfigured: boolean;
  discogsTokenMasked?: string | null;
  lastfmConfigured: boolean;
  lastfmApiKeyMasked?: string | null;
  maxPromptCharacters: number;
  [key: string]: unknown;
}

export interface ConfigurationUpdateRequest {
  plexUrl?: string | null;
  plexToken?: string | null;
  aiProvider?: string | null;
  aiModel?: string | null;
  openaiApiKey?: string | null;
  discogsToken?: string | null;
  lastfmApiKey?: string | null;
}

export interface PlexConnectionTestResponse {
  ok: boolean;
  statusCode?: number | null;
  serverName?: string | null;
  message: string;
}

export interface StatisticsResponse {
  libraries: number;
  artists: number;
  albums: number;
  tracks: number;
  reviews: number;
  averageRating?: number | null;
  cacheEntries: number;
}

export interface PlexSyncStatus {
  running: boolean;
  progress: number;
  libraries: number;
  artists: number;
  albums: number;
  tracks: number;
  lastSync?: string | null;
  error?: string | null;
}

export interface VersionResponse {
  name: string;
  version: string;
  apiVersion: string;
}

export interface LogResponse {
  path: string;
  exists: boolean;
  content: string;
  metadata?: Record<string, unknown>;
}

export interface PromptDebugStats {
  characters: number;
  words: number;
  estimatedTokens: number;
  budget?: number | null;
  promptVersion?: string | null;
}

export interface PromptDebugDocument {
  path: string;
  exists: boolean;
  content: string;
  stats: PromptDebugStats;
}

export interface PromptMetaDocument {
  path: string;
  exists: boolean;
  payload: Record<string, unknown>;
}

export interface ReviewLogDocument {
  path: string;
  exists: boolean;
  content: string;
  sections: Record<string, string>;
}

export interface DeveloperExplanation {
  summary: string[];
  promptSize?: number | null;
  estimatedTokens?: number | null;
  usedSources: Record<string, string>;
  promptDecisions: Record<string, string[]>;
  missedOpportunities: string[];
  recommendations: string[];
}

export interface DeveloperDoctorReport {
  prompt: PromptDebugDocument;
  meta: PromptMetaDocument;
  review: ReviewLogDocument;
  explanation: DeveloperExplanation;
  checks: Record<string, string>;
}

export interface LibraryArtist {
  ratingKey: string;
  title: string;
  library?: string | null;
  albumCount: number;
  trackCount: number;
  summaryPresent: boolean;
  summary?: string | null;
  reviewCount: number;
  plexUrl?: string | null;
  plannedAction?: string | null;
}

export interface LibraryAlbum {
  ratingKey: string;
  title: string;
  artist: string;
  artistId?: string | null;
  library?: string | null;
  year?: number | null;
  trackCount: number;
  genres: string[];
  coverUrl?: string | null;
  reviewStatus: "missing" | "present" | "running" | "error";
  summaryPresent: boolean;
  plannedAction?: string | null;
}

export interface LibraryAlbumDetail extends LibraryAlbum {
  tracks: string[];
  review?: StoredAlbumReview | null;
}

export interface LibraryArtistDetail extends LibraryArtist {
  albums: LibraryAlbum[];
  tracks: string[];
  reviews: StoredAlbumReview[];
}

export interface TokenUsage {
  promptTokens?: number | null;
  completionTokens?: number | null;
  totalTokens?: number | null;
}

export interface PromptAnalysis {
  name: string;
  version: string;
  characters: number;
  estimatedTokens: number;
  budget?: number | null;
  trimmed: boolean;
  budgetDiagnostics: Record<string, unknown>;
  decisions: Record<string, string[]>;
  quality: Record<string, unknown>;
  efficiency?: number | null;
  utilization: Record<string, unknown>;
  evidenceRanking: Record<string, number>;
  evidenceCoverage: Record<string, unknown>;
  editorialCoverage: Record<string, unknown>;
  editorialBalance: Record<string, unknown>;
  missedOpportunities: string[];
}

export interface QualityAnalysis {
  status: string;
  criticalValidation: string;
  editorialValidation: string;
  publishable: boolean;
  wordCount: number;
  checks: Record<string, boolean>;
  warnings: string[];
  failures: string[];
  overallScore?: number | null;
  overallLevel?: string | null;
}

export interface EditorialAnalysis {
  score?: number | null;
  level?: string | null;
  recommendations: string[];
  missingTopics: string[];
  styleMetrics: Record<string, unknown>;
  editorialMetrics: Record<string, unknown>;
}

export interface VerificationAnalysis {
  verifiedFacts: number;
  probableFacts: number;
  weakFacts: number;
  conflictingFacts: number;
  unknownFacts: number;
  coverageScore: number;
  conflicts: string[];
  missingFacts: string[];
}

export interface DebugMeta {
  provider: string;
  model: string;
  generationTimeSeconds: number;
  tokenUsage: TokenUsage;
  sourceCount: number;
  raw: Record<string, unknown>;
}

export interface ReviewDocument {
  apiVersion: string;
  target: ReviewTarget;
  mode: ReviewMode;
  artist: string;
  album?: string | null;
  ratingKey?: string | null;
  currentSummary: string;
  generatedSummary: string;
  proposedSummary: string;
  unifiedDiff: string;
  qa: QualityAnalysis;
  editorial: EditorialAnalysis;
  verification: VerificationAnalysis;
  prompt: PromptAnalysis;
  debug: DebugMeta;
  provider: string;
  model: string;
  edited: boolean;
  plan?: Record<string, unknown> | null;
  context: Record<string, unknown>;
}

export interface ReviewResponse {
  document: ReviewDocument;
  applyAllowed: boolean;
  messages: string[];
}

export interface ApplyResponse {
  status: string;
  artist: string;
  album: string;
  ratingKey: string;
  backupCreated: boolean;
  writeSuccessful: boolean;
  verificationPassed: boolean;
  auditStored: boolean;
  message: string;
  review: ReviewDocument;
}

export interface PreviewResponse {
  document: ReviewDocument;
}

export interface ReviewRequest {
  target: ReviewTarget;
  artist: string;
  album?: string;
  provider?: string;
  model?: string;
  mode?: ReviewMode;
}

export interface ApplyRequest extends ReviewRequest {
  force?: boolean;
}

export interface AlbumReviewContent {
  summary: string;
  rating: number;
  genres: string[];
  strengths: string[];
  weaknesses: string[];
  recommendedFor: string;
  finalVerdict: string;
}

export interface StoredAlbumReview {
  albumId: string;
  artist: string;
  album: string;
  year?: number | null;
  tracks: string[];
  content: AlbumReviewContent;
  provider: string;
  model: string;
  promptName: string;
  promptVersion: string;
  createdAt: string;
}

export interface AlbumReviewListItem {
  albumId: string;
  artist: string;
  album: string;
  year?: number | null;
  trackCount: number;
  reviewStatus: "present" | "missing" | "running" | "error" | string;
  running: boolean;
  error?: string | null;
  rating?: number | null;
  summary?: string | null;
  review?: StoredAlbumReview | null;
}

export interface AlbumReviewOverviewResponse {
  albums: AlbumReviewListItem[];
  generatedReviews: number;
  averageRating?: number | null;
}

export interface AlbumReviewGenerationResponse {
  status: string;
  albumId: string;
}

export type BatchItemStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export interface BatchStartItem {
  target: ReviewTarget;
  plexId: string;
  name: string;
  artist?: string | null;
  album?: string | null;
}

export interface BatchQueueItem extends BatchStartItem {
  id: string;
  status: BatchItemStatus;
  progress: number;
  startedAt?: string | null;
  endedAt?: string | null;
  runtimeSeconds?: number | null;
  error?: string | null;
  reviewId?: string | null;
}

export interface BatchStatusResponse {
  running: boolean;
  cancelled: boolean;
  progress: number;
  active?: BatchQueueItem | null;
  queue: BatchQueueItem[];
  pending: number;
  completed: number;
  failed: number;
  skipped: number;
  total: number;
  estimatedRemainingSeconds?: number | null;
  message?: string | null;
}

export interface BatchHistoryResponse {
  history: BatchQueueItem[];
}
