import { Button, Checkbox, Group, Menu, NativeSelect, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Eye, MoreHorizontal, PencilLine, Play, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { StatusPill } from "../components/StatusPill";
import { useArtists } from "../hooks/useApi";

export function ArtistsPage() {
  const artists = useArtists();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("title");
  const [selected, setSelected] = useState<string[]>([]);
  const rows = useMemo(() => {
    return [...(artists.data ?? [])]
      .filter((artist) => artist.title.toLowerCase().includes(search.toLowerCase()))
      .filter((artist) => (filter === "missing" ? !artist.summaryPresent : filter === "present" ? artist.summaryPresent : true))
      .sort((left, right) => {
        if (sort === "summary") {
          return Number(left.summaryPresent) - Number(right.summaryPresent);
        }
        return left.title.localeCompare(right.title);
      });
  }, [artists.data, filter, search, sort]);

  function toggleSelection(ratingKey: string) {
    setSelected((current) =>
      current.includes(ratingKey) ? current.filter((item) => item !== ratingKey) : [...current, ratingKey],
    );
  }

  function reviewArtist(artist: string) {
    navigate(`/review-workflow?target=artist&artist=${encodeURIComponent(artist)}&run=1`);
  }

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={1}>Künstler</Title>
          <Text c="dimmed">Such- und Review-Vorbereitung für Künstlerbiografien.</Text>
        </div>
        <Group>
          <TextInput placeholder="Künstler suchen" aria-label="Künstler suchen" value={search} onChange={(event) => setSearch(event.currentTarget.value)} />
          <NativeSelect
            aria-label="Filter"
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
            value={sort}
            onChange={(event) => setSort(event.currentTarget.value)}
            data={[
              { value: "title", label: "Name" },
              { value: "summary", label: "Bio-Status" },
            ]}
          />
        </Group>
      </Group>
      <Group justify="space-between" className="selection-bar">
        <Text size="sm" c="dimmed">
          {selected.length} ausgewählt · {rows.length} sichtbar
        </Text>
        <Button leftSection={<RefreshCw size={14} />} size="xs" variant="subtle" onClick={() => void artists.refetch()}>
          Refresh
        </Button>
      </Group>
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
              <Table.Th>Genre</Table.Th>
              <Table.Th>Biografie</Table.Th>
              <Table.Th>Aktionen</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.map((artist) => (
              <Table.Tr
                key={artist.ratingKey}
                onContextMenu={(event) => {
                  event.preventDefault();
                  setSelected([artist.ratingKey]);
                  notifications.show({ message: "Kontextaktionen sind in der Aktionsspalte verfügbar." });
                }}
              >
                <Table.Td>
                  <Checkbox
                    aria-label={`${artist.title} auswählen`}
                    checked={selected.includes(artist.ratingKey)}
                    onChange={() => toggleSelection(artist.ratingKey)}
                  />
                </Table.Td>
                <Table.Td>
                  <div className="cover-placeholder" />
                </Table.Td>
                <Table.Td>{artist.title}</Table.Td>
                <Table.Td>{artist.library ?? "Musik"}</Table.Td>
                <Table.Td>
                  <StatusPill value={artist.summaryPresent} />
                </Table.Td>
                <Table.Td>
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
                <Table.Td colSpan={6}>
                  <Text c="dimmed">Keine Künstler für diese Ansicht gefunden.</Text>
                </Table.Td>
              </Table.Tr>
            ) : null}
          </Table.Tbody>
        </Table>
      </section>
    </Stack>
  );
}
