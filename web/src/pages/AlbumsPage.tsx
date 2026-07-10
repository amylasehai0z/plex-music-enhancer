import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Group,
  Loader,
  Menu,
  NativeSelect,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { Disc3, Eye, MoreHorizontal, PencilLine, Play, RefreshCw, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { StatusPill } from "../components/StatusPill";
import { useAlbum, useAlbumReviewGenerationMutation, useAlbums } from "../hooks/useApi";
import type { LibraryAlbumDetail } from "../types/api";

export function AlbumsPage() {
  const queryClient = useQueryClient();
  const albums = useAlbums();
  const generateReview = useAlbumReviewGenerationMutation();
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

  if (albums.isLoading) {
    return (
      <section className="surface">
        <Group>
          <Loader size="sm" />
          <Text>Alben werden geladen...</Text>
        </Group>
      </section>
    );
  }

  if (albums.isError) {
    return (
      <Alert color="red" title="Alben konnten nicht geladen werden">
        {(albums.error as Error).message}
      </Alert>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={1}>Alben</Title>
          <Text c="dimmed">Synchronized Plex albums with track lists and AI review status.</Text>
        </div>
        <Group>
          <TextInput placeholder="Album suchen" aria-label="Album suchen" value={search} onChange={(event) => setSearch(event.currentTarget.value)} />
          <NativeSelect
            aria-label="Filter"
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
        </Group>
      </Group>
      <Group justify="space-between" className="selection-bar">
        <Text size="sm" c="dimmed">
          {selected.length} ausgewählt · {rows.length} sichtbar
        </Text>
        <Button leftSection={<RefreshCw size={14} />} size="xs" variant="subtle" onClick={() => void albums.refetch()}>
          Refresh
        </Button>
      </Group>
      <SimpleGrid cols={{ base: 1, xl: 2 }} spacing="md">
        <section className="surface table-surface">
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
                    <div className="cover-placeholder" />
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
                    <Text c="dimmed">Keine Alben für diese Ansicht gefunden.</Text>
                  </Table.Td>
                </Table.Tr>
              ) : null}
            </Table.Tbody>
          </Table>
        </section>
        <AlbumDetailPanel
          detail={activeAlbum.data}
          error={activeAlbum.error as Error | null}
          loading={activeAlbum.isLoading}
          generating={generateReview.isPending && generateReview.variables === selectedAlbumId}
          onGenerate={(albumId) => generateAlbumReview(albumId)}
          onOpenArtist={openArtist}
          onReview={(artist, album) => reviewAlbum(artist, album)}
        />
      </SimpleGrid>
    </Stack>
  );
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
  if (loading) {
    return (
      <section className="surface">
        <Group>
          <Loader size="sm" />
          <Text>Albumdetails werden geladen...</Text>
        </Group>
      </section>
    );
  }

  if (error) {
    return (
      <Alert color="red" title="Albumdetails konnten nicht geladen werden">
        {error.message}
      </Alert>
    );
  }

  if (!detail) {
    return (
      <section className="surface">
        <Text c="dimmed">Wähle ein Album aus, um Details anzuzeigen.</Text>
      </section>
    );
  }

  return (
    <section className="surface">
      <Stack gap="md">
        <Group justify="space-between" align="flex-start">
          <div>
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
        </Group>
        <Group grow>
          <Metric label="Jahr" value={detail.year?.toString() ?? "unbekannt"} />
          <Metric label="Tracks" value={detail.trackCount.toLocaleString("de-DE")} />
          <Metric label="Review" value={detail.reviewStatus === "present" ? "vorhanden" : "fehlt"} />
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
              <Text size="sm">{detail.review.content.finalVerdict}</Text>
              <Text size="xs" c="dimmed">
                {detail.review.provider} · {detail.review.model}
              </Text>
            </Stack>
          ) : (
            <Text c="dimmed">Noch kein gespeichertes Review für dieses Album.</Text>
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
    </section>
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text fw={800}>{value}</Text>
    </div>
  );
}
