import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { ReviewRequest } from "../types/api";

export function useDashboardData() {
  const statistics = useQuery({ queryKey: ["statistics"], queryFn: () => api.statistics.get() });
  const providers = useQuery({ queryKey: ["providers"], queryFn: () => api.providers.list() });
  const configuration = useQuery({ queryKey: ["configuration"], queryFn: () => api.config.get() });
  const version = useQuery({ queryKey: ["system", "version"], queryFn: () => api.system.version() });

  return { statistics, providers, configuration, version };
}

export function useArtists() {
  return useQuery({ queryKey: ["artists"], queryFn: () => api.library.artists() });
}

export function useAlbums() {
  return useQuery({ queryKey: ["albums"], queryFn: () => api.library.albums() });
}

export function useReviewMutation() {
  return useMutation({
    mutationFn: (request: ReviewRequest) => api.review.review(request),
  });
}

export function useApplyMutation() {
  return useMutation({
    mutationFn: (request: ReviewRequest) => api.apply.apply(request),
  });
}

export function usePromptLog() {
  return useQuery({ queryKey: ["logs", "prompt"], queryFn: () => api.logs.prompt() });
}

export function useReviewLog() {
  return useQuery({ queryKey: ["logs", "review"], queryFn: () => api.logs.review() });
}

export function useDeveloperExplain() {
  return useQuery({ queryKey: ["debug", "explain"], queryFn: () => api.debug.explain() });
}

export function useDeveloperDoctor() {
  return useQuery({ queryKey: ["debug", "doctor"], queryFn: () => api.debug.doctor() });
}

export function useDebugPrompt() {
  return useQuery({ queryKey: ["debug", "prompt"], queryFn: () => api.debug.prompt() });
}

export function useDebugMeta() {
  return useQuery({ queryKey: ["debug", "meta"], queryFn: () => api.debug.meta() });
}

export function useDebugReview() {
  return useQuery({ queryKey: ["debug", "review"], queryFn: () => api.debug.review() });
}
