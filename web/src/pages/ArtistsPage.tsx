import { Button, Group, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { Eye, PencilLine, Play } from "lucide-react";

import { StatusPill } from "../components/StatusPill";
import { useArtists } from "../hooks/useApi";

export function ArtistsPage() {
  const artists = useArtists();

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={1}>Künstler</Title>
          <Text c="dimmed">Such- und Review-Vorbereitung für Künstlerbiografien.</Text>
        </div>
        <TextInput placeholder="Künstler suchen" aria-label="Künstler suchen" />
      </Group>
      <section className="surface table-surface">
        <Table stickyHeader>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Cover</Table.Th>
              <Table.Th>Name</Table.Th>
              <Table.Th>Genre</Table.Th>
              <Table.Th>Biografie</Table.Th>
              <Table.Th>Aktionen</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(artists.data ?? []).map((artist) => (
              <Table.Tr key={artist.ratingKey}>
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
            {!artists.data?.length ? (
              <Table.Tr>
                <Table.Td colSpan={5}>
                  <Text c="dimmed">Noch keine Künstlerdaten geladen.</Text>
                </Table.Td>
              </Table.Tr>
            ) : null}
          </Table.Tbody>
        </Table>
      </section>
    </Stack>
  );
}
