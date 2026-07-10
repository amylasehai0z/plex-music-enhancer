import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { ReviewRequest } from "../types/api";

export function useDashboardData() {
  const statistics = useQuery({ queryKey: ["statistics"], queryFn: () => api.statistics.get() });
  const providers = useQuery({ queryKey: ["providers"], queryFn: () => api.providers.list() });
  const configuration = useQuery({ queryKey: ["configuration"], queryFn: () => api.config.get() });
  const version = useQuery({ queryKey: ["system", "version"], queryFn: () => api.system.version() });
  const plexSync = useQuery({
    queryKey: ["plex", "sync"],
    queryFn: () => api.plex.syncStatus(),
    refetchInterval: (query) => (query.state.data?.running ? 1000 : false),
  });

  return { statistics, providers, configuration, version, plexSync };
}

export function usePlexSyncMutation() {
  return useMutation({
    mutationFn: () => api.plex.sync(),
  });
}

export function useAlbumReviews() {
  return useQuery({
    queryKey: ["albumReviews"],
    queryFn: () => api.albumReviews.list(),
    refetchInterval: (query) =>
      query.state.data?.albums.some((album) => album.running) ? 1000 : false,
  });
}

export function useAlbumReviewGenerationMutation() {
  return useMutation({
    mutationFn: (albumId: string) => api.albumReviews.generate(albumId),
  });
}

export function useArtists() {
  return useQuery({ queryKey: ["artists"], queryFn: () => api.library.artists() });
}

export function useArtist(artistId: string | null) {
  return useQuery({
    queryKey: ["artists", artistId],
    queryFn: () => api.library.artist(artistId ?? ""),
    enabled: Boolean(artistId),
  });
}

export function useAlbums() {
  return useQuery({ queryKey: ["albums"], queryFn: () => api.library.albums() });
}

export function useAlbum(albumId: string | null) {
  return useQuery({
    queryKey: ["albums", albumId],
    queryFn: () => api.library.album(albumId ?? ""),
    enabled: Boolean(albumId),
  });
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
