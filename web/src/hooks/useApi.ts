import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { ReviewRequest } from "../types/api";

export function useDashboardData() {
  const statistics = useQuery({ queryKey: ["statistics"], queryFn: () => api.statistics.get() });
  const providers = useQuery({ queryKey: ["providers"], queryFn: () => api.providers.list() });
  const configuration = useQuery({ queryKey: ["configuration"], queryFn: () => api.config.get() });

  return { statistics, providers, configuration };
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

export function usePromptLog() {
  return useQuery({ queryKey: ["logs", "prompt"], queryFn: () => api.logs.prompt() });
}

export function useReviewLog() {
  return useQuery({ queryKey: ["logs", "review"], queryFn: () => api.logs.review() });
}
