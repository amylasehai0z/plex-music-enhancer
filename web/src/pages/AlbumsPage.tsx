import { Button, Group, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { Eye, PencilLine, Play } from "lucide-react";

import { StatusPill } from "../components/StatusPill";
import { useAlbums } from "../hooks/useApi";

export function AlbumsPage() {
  const albums = useAlbums();

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={1}>Alben</Title>
          <Text c="dimmed">Albumübersicht mit Review-, Preview- und Apply-Aktionen.</Text>
        </div>
        <TextInput placeholder="Album suchen" aria-label="Album suchen" />
      </Group>
      <section className="surface table-surface">
        <Table stickyHeader>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Cover</Table.Th>
              <Table.Th>Album</Table.Th>
              <Table.Th>Interpret</Table.Th>
              <Table.Th>Jahr</Table.Th>
              <Table.Th>Beschreibung</Table.Th>
              <Table.Th>Aktionen</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(albums.data ?? []).map((album) => (
              <Table.Tr key={album.ratingKey}>
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
                    <Button leftSection={<Play size={16} />} size="xs" variant="light">
                      Review
                    </Button>
                    <Button leftSection={<Eye size={16} />} size="xs" variant="subtle">
                      Preview
                    </Button>
                    <Button leftSection={<PencilLine size={16} />} size="xs" variant="subtle">
                      Apply
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
            {!albums.data?.length ? (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Text c="dimmed">Noch keine Albumdaten geladen.</Text>
                </Table.Td>
              </Table.Tr>
            ) : null}
          </Table.Tbody>
        </Table>
      </section>
    </Stack>
  );
}
