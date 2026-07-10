import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Group,
  Loader,
  Menu,
  NativeSelect,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Eye, MoreHorizontal, Music2, PencilLine, Play, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { StatusPill } from "../components/StatusPill";
import { useArtist, useArtists } from "../hooks/useApi";
import type { LibraryArtistDetail } from "../types/api";

export function ArtistsPage() {
  const artists = useArtists();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("title");
  const [selected, setSelected] = useState<string[]>([]);
  const [activeArtistId, setActiveArtistId] = useState<string | null>(null);
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

  if (artists.isLoading) {
    return (
      <section className="surface">
        <Group>
          <Loader size="sm" />
          <Text>Künstler werden geladen...</Text>
        </Group>
      </section>
    );
  }

  if (artists.isError) {
    return (
      <Alert color="red" title="Künstler konnten nicht geladen werden">
        {(artists.error as Error).message}
      </Alert>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={1}>Künstler</Title>
          <Text c="dimmed">Synchronized Plex artists with albums, tracks and review context.</Text>
        </div>
        <Group align="flex-end">
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
        </Group>
      </Group>
      <Group justify="space-between" className="selection-bar">
        <Group gap="xs">
          <Text size="sm" c="dimmed">
            {selected.length} ausgewählt · {rows.length} sichtbar
          </Text>
          <Badge aria-label="Aktiver Bio-Filter" variant="light">
            {filterLabel(filter)}
          </Badge>
        </Group>
        <Button leftSection={<RefreshCw size={14} />} size="xs" variant="subtle" onClick={() => void artists.refetch()}>
          Refresh
        </Button>
      </Group>
      <div className="library-split-view">
        <section className="surface table-surface">
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
                    <div className="cover-placeholder" />
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
                      <Button leftSection={<Eye size={16} />} size="xs" variant="subtle">
                        Preview
                      </Button>
                      <Button leftSection={<PencilLine size={16} />} size="xs" variant="subtle">
                        Apply
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
                          <Menu.Item leftSection={<Eye size={14} />}>Preview</Menu.Item>
                          <Menu.Item leftSection={<PencilLine size={14} />}>Apply</Menu.Item>
                          <Menu.Item>Open in Plex</Menu.Item>
                          <Menu.Item onClick={() => void artists.refetch()}>Refresh</Menu.Item>
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
        </section>
        <ArtistDetailPanel loading={activeArtist.isLoading} error={activeArtist.error as Error | null} detail={activeArtist.data} />
      </div>
    </Stack>
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
  if (loading) {
    return (
      <section className="surface">
        <Group>
          <Loader size="sm" />
          <Text>Künstlerdetails werden geladen...</Text>
        </Group>
      </section>
    );
  }

  if (error) {
    return (
      <Alert color="red" title="Künstlerdetails konnten nicht geladen werden">
        {error.message}
      </Alert>
    );
  }

  if (!detail) {
    return (
      <section className="surface">
        <Text c="dimmed">Wähle einen Künstler aus, um Details anzuzeigen.</Text>
      </section>
    );
  }

  return (
    <section className="surface">
      <Stack gap="md">
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={2}>{detail.title}</Title>
            <Text c="dimmed">{detail.library ?? "Musikbibliothek"}</Text>
          </div>
          <Badge leftSection={<Music2 size={12} />} variant="light">
            {detail.reviews.length} Reviews
          </Badge>
        </Group>
        <Group grow>
          <Metric label="Alben" value={detail.albumCount} />
          <Metric label="Tracks" value={detail.trackCount} />
          <Metric label="Reviews" value={detail.reviews.length} />
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
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric-card">
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text fw={800}>{value.toLocaleString("de-DE")}</Text>
    </div>
  );
}
