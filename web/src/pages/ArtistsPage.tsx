import {
  Badge,
  Button,
  Checkbox,
  Group,
  Menu,
  Modal,
  NativeSelect,
  ScrollArea,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useQueryClient } from "@tanstack/react-query";
import { ExternalLink, Eye, ListChecks, MoreHorizontal, Music2, PencilLine, Play, RefreshCw } from "lucide-react";
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
import {
  useApplyMutation,
  useArtist,
  useArtistRefreshMutation,
  useArtists,
  useBatchStartMutation,
  usePreviewMutation,
} from "../hooks/useApi";
import type { LibraryArtist, LibraryArtistDetail, ReviewDocument } from "../types/api";

type BusyAction = "preview" | "apply" | "refresh";

export function ArtistsPage() {
  const artists = useArtists();
  const batchStart = useBatchStartMutation();
  const preview = usePreviewMutation();
  const apply = useApplyMutation();
  const refreshArtist = useArtistRefreshMutation();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("title");
  const [selected, setSelected] = useState<string[]>([]);
  const [activeArtistId, setActiveArtistId] = useState<string | null>(null);
  const [busy, setBusy] = useState<{ artistId: string; action: BusyAction } | null>(null);
  const [previewDocument, setPreviewDocument] = useState<ReviewDocument | null>(null);
  const rows = useMemo(() => {
    return [...(artists.data ?? [])]
      .filter((artist) => artist.title.toLowerCase().includes(search.toLowerCase()))
      .filter((artist) => (filter === "missing" ? !artist.summaryPresent : filter === "present" ? artist.summaryPresent : true))
      .sort((left, right) => {
        if (sort === "albums") {
          return right.albumCount - left.albumCount;
        }
        if (sort === "tracks") {
          return right.trackCount - left.trackCount;
        }
        if (sort === "summary") {
          return Number(left.summaryPresent) - Number(right.summaryPresent);
        }
        return left.title.localeCompare(right.title);
      });
  }, [artists.data, filter, search, sort]);
  const selectedArtistId = activeArtistId ?? rows[0]?.ratingKey ?? null;
  const activeArtist = useArtist(selectedArtistId);

  useEffect(() => {
    if (activeArtistId !== null && !rows.some((artist) => artist.ratingKey === activeArtistId)) {
      setActiveArtistId(null);
    }
  }, [activeArtistId, rows]);

  function toggleSelection(ratingKey: string) {
    setSelected((current) =>
      current.includes(ratingKey) ? current.filter((item) => item !== ratingKey) : [...current, ratingKey],
    );
  }

  function reviewArtist(artist: string) {
    navigate(`/review-workflow?target=artist&artist=${encodeURIComponent(artist)}&run=1`);
  }

  function isBusy(artist: LibraryArtist, action: BusyAction) {
    return busy?.artistId === artist.ratingKey && busy.action === action;
  }

  async function refreshSelectedArtist(artist: LibraryArtist) {
    setBusy({ artistId: artist.ratingKey, action: "refresh" });
    try {
      await refreshArtist.mutateAsync(artist.ratingKey);
      await queryClient.invalidateQueries({ queryKey: ["artists"] });
      await queryClient.invalidateQueries({ queryKey: ["artists", artist.ratingKey] });
      notifications.show({ color: "teal", message: `${artist.title} wurde aus Plex aktualisiert.` });
    } catch (error) {
      notifications.show({ color: "red", message: error instanceof Error ? error.message : "Künstler konnte nicht aktualisiert werden." });
    } finally {
      setBusy(null);
    }
  }

  async function previewArtist(artist: LibraryArtist) {
    setBusy({ artistId: artist.ratingKey, action: "preview" });
    try {
      const response = await preview.mutateAsync({ target: "artist", artist: artist.title });
      setPreviewDocument(response.document);
    } catch (error) {
      notifications.show({ color: "red", message: error instanceof Error ? error.message : "Preview konnte nicht erzeugt werden." });
    } finally {
      setBusy(null);
    }
  }

  async function applyArtist(artist: LibraryArtist) {
    setBusy({ artistId: artist.ratingKey, action: "apply" });
    try {
      const response = await apply.mutateAsync({ target: "artist", artist: artist.title });
      if (response.status !== "SUCCESS" || !response.writeSuccessful || !response.verificationPassed) {
        notifications.show({ color: "red", message: response.message || "Plex hat die Änderung nicht bestätigt." });
        return;
      }
      await refreshArtist.mutateAsync(artist.ratingKey);
      await queryClient.invalidateQueries({ queryKey: ["artists"] });
      await queryClient.invalidateQueries({ queryKey: ["artists", artist.ratingKey] });
      notifications.show({ color: "teal", message: "Plex hat die Künstler-Biografie bestätigt." });
    } catch (error) {
      notifications.show({ color: "red", message: error instanceof Error ? error.message : "Apply konnte nicht abgeschlossen werden." });
    } finally {
      setBusy(null);
    }
  }

  function openInPlex(artist: LibraryArtist) {
    if (!artist.plexUrl) {
      notifications.show({ color: "yellow", message: "Plex URL ist nicht konfiguriert." });
      return;
    }
    window.open(artist.plexUrl, "_blank", "noopener,noreferrer");
  }

  function startBatch() {
    const selectedIds = selected.length ? selected : selectedArtistId ? [selectedArtistId] : [];
    const items = rows
      .filter((artist) => selectedIds.includes(artist.ratingKey))
      .map((artist) => ({
        target: "artist" as const,
        plexId: artist.ratingKey,
        name: artist.title,
        artist: artist.title,
      }));
    if (!items.length) {
      notifications.show({ color: "yellow", message: "Wähle mindestens einen Künstler aus." });
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

  if (artists.isLoading) {
    return <LibraryLoadingState label="Künstler werden geladen..." />;
  }

  if (artists.isError) {
    return <LibraryErrorState title="Künstler konnten nicht geladen werden" error={artists.error as Error} />;
  }

  return (
    <>
      <LibraryExplorer
        title="Künstler"
        description="Synchronized Plex artists with albums, tracks and review context."
        toolbar={
        <>
          <TextInput placeholder="Künstler suchen" aria-label="Künstler suchen" value={search} onChange={(event) => setSearch(event.currentTarget.value)} />
          <NativeSelect
            aria-label="Bio-Filter"
            label="Bio"
            value={filter}
            onChange={(event) => setFilter(event.currentTarget.value)}
            data={[
              { value: "all", label: "Alle" },
              { value: "missing", label: "Ohne Bio" },
              { value: "present", label: "Mit Bio" },
            ]}
          />
          <NativeSelect
            aria-label="Sortierung"
            label="Sortierung"
            value={sort}
            onChange={(event) => setSort(event.currentTarget.value)}
            data={[
              { value: "title", label: "Name" },
              { value: "albums", label: "Alben" },
              { value: "tracks", label: "Tracks" },
              { value: "summary", label: "Bio-Status" },
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
          <Badge aria-label="Aktiver Bio-Filter" variant="light">
            {filterLabel(filter)}
          </Badge>
        </Group>
        <Button
          leftSection={<RefreshCw size={14} />}
          size="xs"
          variant="subtle"
          disabled={!selectedArtistId}
          loading={Boolean(busy && busy.action === "refresh")}
          onClick={() => {
            const artist = rows.find((item) => item.ratingKey === selectedArtistId);
            if (artist) {
              void refreshSelectedArtist(artist);
            }
          }}
        >
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
                    aria-label="Alle sichtbaren Künstler auswählen"
                    checked={rows.length > 0 && selected.length === rows.length}
                    onChange={(event) => setSelected(event.currentTarget.checked ? rows.map((artist) => artist.ratingKey) : [])}
                  />
                </Table.Th>
                <Table.Th>Cover</Table.Th>
                <Table.Th>Name</Table.Th>
                <Table.Th>Alben</Table.Th>
                <Table.Th>Tracks</Table.Th>
                <Table.Th>Biografie</Table.Th>
                <Table.Th>Aktionen</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.map((artist) => (
                <Table.Tr
                  key={artist.ratingKey}
                  data-active={artist.ratingKey === selectedArtistId ? "true" : undefined}
                  onClick={() => setActiveArtistId(artist.ratingKey)}
                  onContextMenu={(event) => {
                    event.preventDefault();
                    setSelected([artist.ratingKey]);
                    setActiveArtistId(artist.ratingKey);
                    notifications.show({ message: "Kontextaktionen sind in der Aktionsspalte verfügbar." });
                  }}
                >
                  <Table.Td>
                    <Checkbox
                      aria-label={`${artist.title} auswählen`}
                      checked={selected.includes(artist.ratingKey)}
                      onChange={() => toggleSelection(artist.ratingKey)}
                      onClick={(event) => event.stopPropagation()}
                    />
                  </Table.Td>
                  <Table.Td>
                    <CoverArt label={`${artist.title} Cover`} />
                  </Table.Td>
                  <Table.Td>{artist.title}</Table.Td>
                  <Table.Td>{artist.albumCount}</Table.Td>
                  <Table.Td>{artist.trackCount}</Table.Td>
                  <Table.Td>
                    <StatusPill value={artist.summaryPresent} />
                  </Table.Td>
                  <Table.Td onClick={(event) => event.stopPropagation()}>
                    <Group gap="xs">
                      <Button leftSection={<Play size={16} />} size="xs" variant="light" onClick={() => reviewArtist(artist.title)}>
                        Review
                      </Button>
                      <Button
                        leftSection={<Eye size={16} />}
                        size="xs"
                        variant="subtle"
                        loading={isBusy(artist, "preview")}
                        onClick={() => void previewArtist(artist)}
                      >
                        Preview
                      </Button>
                      <Button
                        leftSection={<PencilLine size={16} />}
                        size="xs"
                        variant="subtle"
                        loading={isBusy(artist, "apply")}
                        onClick={() => void applyArtist(artist)}
                      >
                        Apply
                      </Button>
                      <Button leftSection={<ExternalLink size={16} />} size="xs" variant="subtle" onClick={() => openInPlex(artist)}>
                        Plex
                      </Button>
                      <Menu shadow="md" width={180}>
                        <Menu.Target>
                          <Button size="xs" variant="subtle" aria-label="Kontextmenü">
                            <MoreHorizontal size={16} />
                          </Button>
                        </Menu.Target>
                        <Menu.Dropdown>
                          <Menu.Item leftSection={<Play size={14} />} onClick={() => reviewArtist(artist.title)}>
                            Review
                          </Menu.Item>
                          <Menu.Item leftSection={<Eye size={14} />} onClick={() => void previewArtist(artist)}>
                            Preview
                          </Menu.Item>
                          <Menu.Item leftSection={<PencilLine size={14} />} onClick={() => void applyArtist(artist)}>
                            Apply
                          </Menu.Item>
                          <Menu.Item leftSection={<ExternalLink size={14} />} onClick={() => openInPlex(artist)}>
                            Open in Plex
                          </Menu.Item>
                          <Menu.Item onClick={() => void refreshSelectedArtist(artist)}>Refresh</Menu.Item>
                        </Menu.Dropdown>
                      </Menu>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
              {!rows.length ? (
                <Table.Tr>
                  <Table.Td colSpan={7}>
                    <Text c="dimmed">Keine Künstler gefunden.</Text>
                  </Table.Td>
                </Table.Tr>
              ) : null}
            </Table.Tbody>
          </Table>
      }
        detail={
          <ArtistDetailPanel loading={activeArtist.isLoading} error={activeArtist.error as Error | null} detail={activeArtist.data} />
        }
      />
      <PreviewModal document={previewDocument} onClose={() => setPreviewDocument(null)} />
    </>
  );
}

function filterLabel(filter: string) {
  if (filter === "missing") {
    return "Ohne Bio";
  }
  if (filter === "present") {
    return "Mit Bio";
  }
  return "Alle Künstler";
}

function ArtistDetailPanel({
  detail,
  error,
  loading,
}: {
  detail?: LibraryArtistDetail;
  error: Error | null;
  loading: boolean;
}) {
  return (
    <LibraryDetailState
      loading={loading}
      loadingLabel="Künstlerdetails werden geladen..."
      error={error}
      errorTitle="Künstlerdetails konnten nicht geladen werden"
      empty={<Text c="dimmed">Wähle einen Künstler aus, um Details anzuzeigen.</Text>}
    >
      {detail ? (
      <Stack gap="md">
        <div className="library-detail-header">
          <CoverArt label={`${detail.title} Cover`} size="lg" />
          <div className="library-detail-title">
            <Title order={2}>{detail.title}</Title>
            <Text c="dimmed" size="sm">
              {detail.library ?? "Musikbibliothek"}
            </Text>
          </div>
          <Badge leftSection={<Music2 size={12} />} variant="light">
            {detail.reviews.length} Reviews
          </Badge>
        </div>
        <Group grow>
          <DetailMetric label="Alben" value={detail.albumCount.toLocaleString("de-DE")} />
          <DetailMetric label="Tracks" value={detail.trackCount.toLocaleString("de-DE")} />
          <DetailMetric label="Reviews" value={detail.reviews.length.toLocaleString("de-DE")} />
        </Group>
        <div>
          <Text fw={700} mb="xs">
            Alben
          </Text>
          <Stack gap={4}>
            {detail.albums.slice(0, 8).map((album) => (
              <Text key={album.ratingKey} size="sm">
                {album.title}
                {album.year ? ` (${album.year})` : ""}
              </Text>
            ))}
            {!detail.albums.length ? <Text c="dimmed">Keine Alben im Sync-Snapshot vorhanden.</Text> : null}
          </Stack>
        </div>
        <div>
          <Text fw={700} mb="xs">
            Tracks
          </Text>
          <Text size="sm" c="dimmed">
            {detail.tracks.slice(0, 12).join(" · ") || "Keine Tracks im Sync-Snapshot vorhanden."}
          </Text>
        </div>
        <div>
          <Text fw={700} mb="xs">
            Biografie
          </Text>
          <Text size="sm" c={detail.summary ? undefined : "dimmed"}>
            {detail.summary || "Keine Biografie im Sync-/Review-Kontext vorhanden."}
          </Text>
        </div>
        <div>
          <Text fw={700} mb="xs">
            Vorhandene Reviews
          </Text>
          <Stack gap={4}>
            {detail.reviews.map((review) => (
              <Text key={review.albumId} size="sm">
                {review.album}: {review.content.rating}/100
              </Text>
            ))}
            {!detail.reviews.length ? <Text c="dimmed">Noch keine gespeicherten Albumreviews für diesen Künstler.</Text> : null}
          </Stack>
        </div>
      </Stack>
      ) : null}
    </LibraryDetailState>
  );
}

function PreviewModal({ document, onClose }: { document: ReviewDocument | null; onClose: () => void }) {
  return (
    <Modal opened={Boolean(document)} onClose={onClose} title="Künstler-Preview" size="xl">
      {document ? (
        <Stack gap="md">
          <Group justify="space-between">
            <div>
              <Title order={3}>{document.artist}</Title>
              <Text c="dimmed" size="sm">
                {document.provider} · {document.model}
              </Text>
            </div>
            <Badge variant="light">{document.qa.status}</Badge>
          </Group>
          <Group align="stretch" grow>
            <SummaryBlock title="Aktuelle Plex-Biografie" value={document.currentSummary || "Keine aktuelle Biografie."} />
            <SummaryBlock title="Generierte Biografie" value={document.generatedSummary} />
          </Group>
          <div>
            <Text fw={700} mb="xs">
              Diff
            </Text>
            <ScrollArea.Autosize mah={220}>
              <pre className="debug-pre">{document.unifiedDiff}</pre>
            </ScrollArea.Autosize>
          </div>
        </Stack>
      ) : null}
    </Modal>
  );
}

function SummaryBlock({ title, value }: { title: string; value: string }) {
  return (
    <div>
      <Text fw={700} mb="xs">
        {title}
      </Text>
      <ScrollArea.Autosize mah={260}>
        <Text size="sm">{value}</Text>
      </ScrollArea.Autosize>
    </div>
  );
}
