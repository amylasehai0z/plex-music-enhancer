import type {
  ApplyRequest,
  ConfigurationUpdateRequest,
  ConfigurationResponse,
  DeveloperDoctorReport,
  DeveloperExplanation,
  LibraryAlbum,
  LibraryArtist,
  LogResponse,
  PlexConnectionTestResponse,
  PromptDebugDocument,
  PromptMetaDocument,
  PreviewResponse,
  ProviderInfo,
  ReviewRequest,
  ReviewLogDocument,
  ReviewResponse,
  StatisticsResponse,
  VersionResponse,
} from "../types/api";

const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly payload: unknown,
  ) {
    super(message);
  }
}

export class ApiClient {
  constructor(private readonly baseUrl = API_PREFIX) {}

  async get<T>(path: string): Promise<T> {
    return this.request<T>(path);
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  async put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, init);
    const contentType = response.headers.get("content-type") ?? "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      const message =
        typeof payload === "object" && payload !== null && "message" in payload
          ? String(payload.message)
          : `Request failed with status ${response.status}`;
      throw new ApiError(message, response.status, payload);
    }
    return payload as T;
  }
}

export class ReviewApi {
  constructor(private readonly client: ApiClient) {}

  review(request: ReviewRequest): Promise<ReviewResponse> {
    const { target, ...payload } = request;
    return this.client.post<ReviewResponse>(`/review/${target}`, payload);
  }
}

export class PreviewApi {
  constructor(private readonly client: ApiClient) {}

  preview(request: ReviewRequest): Promise<PreviewResponse> {
    return this.client.post<PreviewResponse>("/preview", request);
  }
}

export class ApplyApi {
  constructor(private readonly client: ApiClient) {}

  apply(request: ApplyRequest): Promise<unknown> {
    return this.client.post("/apply", request);
  }
}

export class ConfigApi {
  constructor(private readonly client: ApiClient) {}

  get(): Promise<ConfigurationResponse> {
    return this.client.get<ConfigurationResponse>("/config");
  }

  update(configuration: ConfigurationUpdateRequest): Promise<ConfigurationResponse> {
    return this.client.put<ConfigurationResponse>("/config", configuration);
  }

  testPlex(configuration: ConfigurationUpdateRequest): Promise<PlexConnectionTestResponse> {
    return this.client.post<PlexConnectionTestResponse>("/config/test-plex", configuration);
  }
}

export class ProviderApi {
  constructor(private readonly client: ApiClient) {}

  list(): Promise<ProviderInfo[]> {
    return this.client.get<ProviderInfo[]>("/providers");
  }
}

export class LibraryApi {
  constructor(private readonly client: ApiClient) {}

  artists(): Promise<LibraryArtist[]> {
    return this.client.get<LibraryArtist[]>("/artists");
  }

  albums(): Promise<LibraryAlbum[]> {
    return this.client.get<LibraryAlbum[]>("/albums");
  }
}

export class StatisticsApi {
  constructor(private readonly client: ApiClient) {}

  get(): Promise<StatisticsResponse> {
    return this.client.get<StatisticsResponse>("/statistics");
  }
}

export class SystemApi {
  constructor(private readonly client: ApiClient) {}

  version(): Promise<VersionResponse> {
    return this.client.get<VersionResponse>("/system/version");
  }
}

export class LogApi {
  constructor(private readonly client: ApiClient) {}

  prompt(): Promise<LogResponse> {
    return this.client.get<LogResponse>("/logs/prompt");
  }

  review(): Promise<LogResponse> {
    return this.client.get<LogResponse>("/logs/review");
  }
}

export class DebugApi {
  constructor(private readonly client: ApiClient) {}

  prompt(): Promise<PromptDebugDocument> {
    return this.client.get<PromptDebugDocument>("/debug/prompt");
  }

  meta(): Promise<PromptMetaDocument> {
    return this.client.get<PromptMetaDocument>("/debug/meta");
  }

  review(): Promise<ReviewLogDocument> {
    return this.client.get<ReviewLogDocument>("/debug/review");
  }

  explain(): Promise<DeveloperExplanation> {
    return this.client.get<DeveloperExplanation>("/debug/explain");
  }

  doctor(): Promise<DeveloperDoctorReport> {
    return this.client.get<DeveloperDoctorReport>("/debug/doctor");
  }
}

const client = new ApiClient();

export const api = {
  client,
  review: new ReviewApi(client),
  preview: new PreviewApi(client),
  apply: new ApplyApi(client),
  config: new ConfigApi(client),
  providers: new ProviderApi(client),
  library: new LibraryApi(client),
  statistics: new StatisticsApi(client),
  system: new SystemApi(client),
  logs: new LogApi(client),
  debug: new DebugApi(client),
};
