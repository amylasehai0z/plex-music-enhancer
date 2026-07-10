import { Button, Checkbox, Group, Menu, NativeSelect, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Eye, MoreHorizontal, PencilLine, Play, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { StatusPill } from "../components/StatusPill";
import { useAlbums } from "../hooks/useApi";

export function AlbumsPage() {
  const albums = useAlbums();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("title");
  const [selected, setSelected] = useState<string[]>([]);
  const rows = useMemo(() => {
    return [...(albums.data ?? [])]
      .filter((album) => `${album.title} ${album.artist}`.toLowerCase().includes(search.toLowerCase()))
      .filter((album) => (filter === "missing" ? !album.summaryPresent : filter === "present" ? album.summaryPresent : true))
      .sort((left, right) => {
        if (sort === "year") {
          return (right.year ?? 0) - (left.year ?? 0);
        }
        if (sort === "artist") {
          return left.artist.localeCompare(right.artist);
        }
        return left.title.localeCompare(right.title);
      });
  }, [albums.data, filter, search, sort]);

  function toggleSelection(ratingKey: string) {
    setSelected((current) =>
      current.includes(ratingKey) ? current.filter((item) => item !== ratingKey) : [...current, ratingKey],
    );
  }

  function reviewAlbum(artist: string, album: string) {
    navigate(`/reviews?target=album&artist=${encodeURIComponent(artist)}&album=${encodeURIComponent(album)}&run=1`);
  }

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={1}>Alben</Title>
          <Text c="dimmed">Albumübersicht mit Review-, Preview- und Apply-Aktionen.</Text>
        </div>
        <Group>
          <TextInput placeholder="Album suchen" aria-label="Album suchen" value={search} onChange={(event) => setSearch(event.currentTarget.value)} />
          <NativeSelect
            aria-label="Filter"
            value={filter}
            onChange={(event) => setFilter(event.currentTarget.value)}
            data={[
              { value: "all", label: "Alle" },
              { value: "missing", label: "Ohne Beschreibung" },
              { value: "present", label: "Mit Beschreibung" },
            ]}
          />
          <NativeSelect
            aria-label="Sortierung"
            value={sort}
            onChange={(event) => setSort(event.currentTarget.value)}
            data={[
              { value: "title", label: "Album" },
              { value: "artist", label: "Interpret" },
              { value: "year", label: "Jahr" },
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
              <Table.Th>Interpret</Table.Th>
              <Table.Th>Jahr</Table.Th>
              <Table.Th>Beschreibung</Table.Th>
              <Table.Th>Aktionen</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.map((album) => (
              <Table.Tr
                key={album.ratingKey}
                onContextMenu={(event) => {
                  event.preventDefault();
                  setSelected([album.ratingKey]);
                  notifications.show({ message: "Kontextaktionen sind in der Aktionsspalte verfügbar." });
                }}
              >
                <Table.Td>
                  <Checkbox
                    aria-label={`${album.title} auswählen`}
                    checked={selected.includes(album.ratingKey)}
                    onChange={() => toggleSelection(album.ratingKey)}
                  />
                </Table.Td>
                <Table.Td>
                  <div className="cover-placeholder" />
                </Table.Td>
                <Table.Td>{album.title}</Table.Td>
                <Table.Td>{album.artist}</Table.Td>
                <Table.Td>{album.year ?? "unbekannt"}</Table.Td>
                <Table.Td>
                  <StatusPill value={album.summaryPresent} />
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button
                      leftSection={<Play size={16} />}
                      size="xs"
                      variant="light"
                      onClick={() => reviewAlbum(album.artist, album.title)}
                    >
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
                        <Menu.Item leftSection={<Play size={14} />} onClick={() => reviewAlbum(album.artist, album.title)}>
                          Review
                        </Menu.Item>
                        <Menu.Item leftSection={<Eye size={14} />}>Preview</Menu.Item>
                        <Menu.Item leftSection={<PencilLine size={14} />}>Apply</Menu.Item>
                        <Menu.Item>Open in Plex</Menu.Item>
                        <Menu.Item onClick={() => void albums.refetch()}>Refresh</Menu.Item>
                      </Menu.Dropdown>
                    </Menu>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
            {!rows.length ? (
              <Table.Tr>
                <Table.Td colSpan={7}>
                  <Text c="dimmed">Keine Alben für diese Ansicht gefunden.</Text>
                </Table.Td>
              </Table.Tr>
            ) : null}
          </Table.Tbody>
        </Table>
      </section>
    </Stack>
  );
}
