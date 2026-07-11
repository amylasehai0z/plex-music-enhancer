import {
  Badge,
  Button,
  Checkbox,
  Group,
  Menu,
  NativeSelect,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { Disc3, Eye, ListChecks, MoreHorizontal, PencilLine, Play, RefreshCw, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { StatusPill } from "../components/StatusPill";
import {
  CoverArt,
  DetailMetric,
  LibraryDetailState,
  LibraryErrorState,
  LibraryExplorer,
  LibraryLoadingState,
} from "../components/LibraryExplorer";
import { useAlbum, useAlbumReviewGenerationMutation, useAlbums, useBatchStartMutation } from "../hooks/useApi";
import type { LibraryAlbumDetail } from "../types/api";

export function AlbumsPage() {
  const queryClient = useQueryClient();
  const albums = useAlbums();
  const generateReview = useAlbumReviewGenerationMutation();
  const batchStart = useBatchStartMutation();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("title");
  const [selected, setSelected] = useState<string[]>([]);
  const [activeAlbumId, setActiveAlbumId] = useState<string | null>(null);
  const rows = useMemo(() => {
    return [...(albums.data ?? [])]
      .filter((album) => `${album.title} ${album.artist}`.toLowerCase().includes(search.toLowerCase()))
      .filter((album) => {
        if (filter === "missing") {
          return album.reviewStatus !== "present";
        }
        if (filter === "present") {
          return album.reviewStatus === "present";
        }
        return true;
      })
      .sort((left, right) => {
        if (sort === "year") {
          return (right.year ?? 0) - (left.year ?? 0);
        }
        if (sort === "artist") {
          return left.artist.localeCompare(right.artist) || left.title.localeCompare(right.title);
        }
        if (sort === "tracks") {
          return right.trackCount - left.trackCount;
        }
        if (sort === "review") {
          return left.reviewStatus.localeCompare(right.reviewStatus) || left.title.localeCompare(right.title);
        }
        return left.title.localeCompare(right.title);
      });
  }, [albums.data, filter, search, sort]);
  const selectedAlbumId = activeAlbumId ?? rows[0]?.ratingKey ?? null;
  const activeAlbum = useAlbum(selectedAlbumId);

  useEffect(() => {
    if (activeAlbumId !== null && !rows.some((album) => album.ratingKey === activeAlbumId)) {
      setActiveAlbumId(null);
    }
  }, [activeAlbumId, rows]);

  function toggleSelection(ratingKey: string) {
    setSelected((current) =>
      current.includes(ratingKey) ? current.filter((item) => item !== ratingKey) : [...current, ratingKey],
    );
  }

  function reviewAlbum(artist: string, album: string) {
    navigate(`/review-workflow?target=album&artist=${encodeURIComponent(artist)}&album=${encodeURIComponent(album)}&run=1`);
  }

  function openArtist(artist: string) {
    navigate(`/artists?search=${encodeURIComponent(artist)}`);
  }

  function generateAlbumReview(albumId: string) {
    generateReview.mutate(albumId, {
      onSuccess: async () => {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ["albums"] }),
          queryClient.invalidateQueries({ queryKey: ["albums", albumId] }),
          queryClient.invalidateQueries({ queryKey: ["albumReviews"] }),
          queryClient.invalidateQueries({ queryKey: ["statistics"] }),
        ]);
        notifications.show({ message: "Review-Erzeugung wurde gestartet." });
      },
    });
  }

  function startBatch() {
    const selectedIds = selected.length ? selected : selectedAlbumId ? [selectedAlbumId] : [];
    const items = rows
      .filter((album) => selectedIds.includes(album.ratingKey))
      .map((album) => ({
        target: "album" as const,
        plexId: album.ratingKey,
        name: album.title,
        artist: album.artist,
        album: album.title,
      }));
    if (!items.length) {
      notifications.show({ color: "yellow", message: "Wähle mindestens ein Album aus." });
      return;
    }
    batchStart.mutate(items, {
      onSuccess: () => {
        notifications.show({ color: "teal", message: "Batch wurde gestartet." });
        navigate("/batch");
      },
      onError: (error) => notifications.show({ color: "red", message: error.message }),
    });
  }

  if (albums.isLoading) {
    return <LibraryLoadingState label="Alben werden geladen..." />;
  }

  if (albums.isError) {
    return <LibraryErrorState title="Alben konnten nicht geladen werden" error={albums.error as Error} />;
  }

  return (
    <LibraryExplorer
      title="Alben"
      description="Synchronized Plex albums with track lists and AI review status."
      toolbar={
        <>
          <TextInput placeholder="Album suchen" aria-label="Album suchen" value={search} onChange={(event) => setSearch(event.currentTarget.value)} />
          <NativeSelect
            aria-label="Review-Filter"
            label="Review"
            value={filter}
            onChange={(event) => setFilter(event.currentTarget.value)}
            data={[
              { value: "all", label: "Alle" },
              { value: "missing", label: "Ohne Review" },
              { value: "present", label: "Mit Review" },
            ]}
          />
          <NativeSelect
            aria-label="Sortierung"
            label="Sortierung"
            value={sort}
            onChange={(event) => setSort(event.currentTarget.value)}
            data={[
              { value: "title", label: "Album" },
              { value: "artist", label: "Künstler" },
              { value: "year", label: "Jahr" },
              { value: "tracks", label: "Tracks" },
              { value: "review", label: "Review-Status" },
            ]}
          />
        </>
      }
      meta={
        <>
        <Group gap="xs">
          <Text size="sm" c="dimmed">
            {selected.length} ausgewählt · {rows.length} sichtbar
          </Text>
          <Badge aria-label="Aktiver Review-Filter" variant="light">
            {filterLabel(filter)}
          </Badge>
        </Group>
        <Button leftSection={<RefreshCw size={14} />} size="xs" variant="subtle" onClick={() => void albums.refetch()}>
          Refresh
        </Button>
        <Button leftSection={<ListChecks size={14} />} size="xs" variant="light" loading={batchStart.isPending} onClick={startBatch}>
          Batch starten
        </Button>
        </>
      }
      list={
        <Table stickyHeader>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>
                  <Checkbox
                    aria-label="Alle sichtbaren Alben auswählen"
                    checked={rows.length > 0 && selected.length === rows.length}
                    onChange={(event) => setSelected(event.currentTarget.checked ? rows.map((album) => album.ratingKey) : [])}
                  />
                </Table.Th>
                <Table.Th>Cover</Table.Th>
                <Table.Th>Album</Table.Th>
                <Table.Th>Künstler</Table.Th>
                <Table.Th>Jahr</Table.Th>
                <Table.Th>Tracks</Table.Th>
                <Table.Th>Review</Table.Th>
                <Table.Th>Aktionen</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.map((album) => (
                <Table.Tr
                  key={album.ratingKey}
                  data-active={album.ratingKey === selectedAlbumId ? "true" : undefined}
                  onClick={() => setActiveAlbumId(album.ratingKey)}
                  onContextMenu={(event) => {
                    event.preventDefault();
                    setSelected([album.ratingKey]);
                    setActiveAlbumId(album.ratingKey);
                    notifications.show({ message: "Kontextaktionen sind in der Aktionsspalte verfügbar." });
                  }}
                >
                  <Table.Td>
                    <Checkbox
                      aria-label={`${album.title} auswählen`}
                      checked={selected.includes(album.ratingKey)}
                      onChange={() => toggleSelection(album.ratingKey)}
                      onClick={(event) => event.stopPropagation()}
                  />
                </Table.Td>
                <Table.Td>
                    <CoverArt label={`${album.title} Cover`} src={album.coverUrl} />
                </Table.Td>
                  <Table.Td>{album.title}</Table.Td>
                  <Table.Td>{album.artist}</Table.Td>
                  <Table.Td>{album.year ?? "unbekannt"}</Table.Td>
                  <Table.Td>{album.trackCount}</Table.Td>
                  <Table.Td>
                    <ReviewStatus status={album.reviewStatus} />
                  </Table.Td>
                  <Table.Td onClick={(event) => event.stopPropagation()}>
                    <Group gap="xs">
                      <Button leftSection={<Play size={16} />} size="xs" variant="light" onClick={() => reviewAlbum(album.artist, album.title)}>
                        Review
                      </Button>
                      <Button
                        leftSection={<Sparkles size={16} />}
                        size="xs"
                        variant="subtle"
                        loading={generateReview.isPending && generateReview.variables === album.ratingKey}
                        disabled={album.reviewStatus === "present" || album.reviewStatus === "running"}
                        onClick={() => generateAlbumReview(album.ratingKey)}
                      >
                        Erzeugen
                      </Button>
                      <Menu shadow="md" width={180}>
                        <Menu.Target>
                          <Button size="xs" variant="subtle" aria-label="Kontextmenü">
                            <MoreHorizontal size={16} />
                          </Button>
                        </Menu.Target>
                        <Menu.Dropdown>
                          <Menu.Item leftSection={<Play size={14} />} onClick={() => reviewAlbum(album.artist, album.title)}>
                            Review öffnen
                          </Menu.Item>
                          <Menu.Item leftSection={<Eye size={14} />}>Preview</Menu.Item>
                          <Menu.Item leftSection={<PencilLine size={14} />}>Apply</Menu.Item>
                          <Menu.Item onClick={() => openArtist(album.artist)}>Künstler öffnen</Menu.Item>
                          <Menu.Item onClick={() => void albums.refetch()}>Refresh</Menu.Item>
                        </Menu.Dropdown>
                      </Menu>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
              {!rows.length ? (
                <Table.Tr>
                  <Table.Td colSpan={8}>
                    <Text c="dimmed">Keine Alben gefunden.</Text>
                  </Table.Td>
                </Table.Tr>
              ) : null}
            </Table.Tbody>
          </Table>
      }
      detail={
        <AlbumDetailPanel
          detail={activeAlbum.data}
          error={activeAlbum.error as Error | null}
          loading={activeAlbum.isLoading}
          generating={generateReview.isPending && generateReview.variables === selectedAlbumId}
          onGenerate={(albumId) => generateAlbumReview(albumId)}
          onOpenArtist={openArtist}
          onReview={(artist, album) => reviewAlbum(artist, album)}
        />
      }
    />
  );
}

function filterLabel(filter: string) {
  if (filter === "missing") {
    return "Ohne Review";
  }
  if (filter === "present") {
    return "Mit Review";
  }
  return "Alle Alben";
}

function AlbumDetailPanel({
  detail,
  error,
  generating,
  loading,
  onGenerate,
  onOpenArtist,
  onReview,
}: {
  detail?: LibraryAlbumDetail;
  error: Error | null;
  generating: boolean;
  loading: boolean;
  onGenerate: (albumId: string) => void;
  onOpenArtist: (artist: string) => void;
  onReview: (artist: string, album: string) => void;
}) {
  return (
    <LibraryDetailState
      loading={loading}
      loadingLabel="Albumdetails werden geladen..."
      error={error}
      errorTitle="Albumdetails konnten nicht geladen werden"
      empty={<Text c="dimmed">Wähle ein Album aus, um Details anzuzeigen.</Text>}
    >
      {detail ? (
        <Stack gap="md">
          <div className="library-detail-header">
            <CoverArt label={`${detail.title} Cover`} src={detail.coverUrl} size="lg" />
            <div className="library-detail-title">
              <Title order={2}>{detail.title}</Title>
              <Button variant="subtle" size="compact-sm" px={0} onClick={() => onOpenArtist(detail.artist)}>
                {detail.artist}
              </Button>
              <Text c="dimmed" size="sm">
                {[detail.year ?? "Jahr unbekannt", detail.library ?? "Musikbibliothek"].join(" · ")}
              </Text>
            </div>
            <Badge leftSection={<Disc3 size={12} />} variant="light">
              {detail.trackCount} Tracks
            </Badge>
          </div>
          <Group grow>
            <DetailMetric label="Jahr" value={detail.year?.toString() ?? "unbekannt"} />
            <DetailMetric label="Tracks" value={detail.trackCount.toLocaleString("de-DE")} />
            <DetailMetric label="Review" value={detail.reviewStatus === "present" ? "vorhanden" : "fehlt"} />
          </Group>
          <div>
            <Text fw={700} mb="xs">
              Genres
            </Text>
            <Group gap="xs">
              {detail.genres.map((genre) => (
                <Badge key={genre} variant="light">
                  {genre}
                </Badge>
              ))}
              {!detail.genres.length ? <Text c="dimmed">Keine Genres im Sync-/Review-Kontext vorhanden.</Text> : null}
            </Group>
          </div>
          <div>
            <Text fw={700} mb="xs">
              Trackliste
            </Text>
            <Stack gap={4}>
              {detail.tracks.map((track) => (
                <Text key={track} size="sm">
                  {track}
                </Text>
              ))}
              {!detail.tracks.length ? <Text c="dimmed">Keine Tracks im Sync-Snapshot vorhanden.</Text> : null}
            </Stack>
          </div>
          <div>
            <Group justify="space-between" mb="xs">
              <Text fw={700}>AI Review</Text>
              <ReviewStatus status={detail.reviewStatus} />
            </Group>
            {detail.review ? (
              <Stack gap={4}>
                <Text size="sm">{detail.review.content.summary}</Text>
                <Text size="sm" fw={700}>
                  {detail.review.content.rating}/100
                </Text>
                <Text size="sm">
                  <Text span fw={700}>
                    Genres:
                  </Text>{" "}
                  {detail.review.content.genres.join(", ") || "keine Angabe"}
                </Text>
                <Text size="sm">
                  <Text span fw={700}>
                    Strengths:
                  </Text>{" "}
                  {detail.review.content.strengths.join(", ") || "keine Angabe"}
                </Text>
                <Text size="sm">
                  <Text span fw={700}>
                    Weaknesses:
                  </Text>{" "}
                  {detail.review.content.weaknesses.join(", ") || "keine Angabe"}
                </Text>
                <Text size="sm">{detail.review.content.finalVerdict}</Text>
                <Text size="xs" c="dimmed">
                  {detail.review.provider} · {detail.review.model}
                </Text>
              </Stack>
            ) : (
              <Stack gap="xs">
                <Text c="dimmed">Noch kein gespeichertes Review für dieses Album.</Text>
                <Button
                  leftSection={<Sparkles size={16} />}
                  variant="light"
                  loading={generating}
                  disabled={detail.reviewStatus === "running"}
                  onClick={() => onGenerate(detail.ratingKey)}
                >
                  Review generieren
                </Button>
              </Stack>
            )}
          </div>
          <Group>
            <Button leftSection={<Play size={16} />} variant="light" onClick={() => onReview(detail.artist, detail.title)}>
              Review öffnen
            </Button>
            <Button
              leftSection={<Sparkles size={16} />}
              variant="subtle"
              loading={generating}
              disabled={detail.reviewStatus === "present" || detail.reviewStatus === "running"}
              onClick={() => onGenerate(detail.ratingKey)}
            >
              Review erzeugen
            </Button>
          </Group>
        </Stack>
      ) : null}
    </LibraryDetailState>
  );
}

function ReviewStatus({ status }: { status: LibraryAlbumDetail["reviewStatus"] }) {
  if (status === "present") {
    return <StatusPill value />;
  }
  if (status === "running") {
    return <Badge color="blue">läuft</Badge>;
  }
  if (status === "error") {
    return <Badge color="red">Fehler</Badge>;
  }
  return <Badge color="gray">fehlt</Badge>;
}
