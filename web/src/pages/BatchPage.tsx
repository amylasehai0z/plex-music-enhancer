import { Alert, Badge, Button, Group, Progress, Skeleton, Stack, Table, Text, Title } from "@mantine/core";
import { useQueryClient } from "@tanstack/react-query";
import { Ban, RefreshCw, RotateCcw, Trash2 } from "lucide-react";

import { StatusPill } from "../components/StatusPill";
import { useBatchCancelMutation, useBatchClearMutation, useBatchHistory, useBatchStatus } from "../hooks/useApi";
import type { BatchQueueItem } from "../types/api";

export function BatchPage() {
  const queryClient = useQueryClient();
  const status = useBatchStatus();
  const history = useBatchHistory();
  const cancelMutation = useBatchCancelMutation();
  const clearMutation = useBatchClearMutation();
  const batch = status.data;

  async function refresh() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["batch", "status"] }),
      queryClient.invalidateQueries({ queryKey: ["batch", "history"] }),
    ]);
  }

  function cancel() {
    cancelMutation.mutate(undefined, { onSuccess: () => void refresh() });
  }

  function clear() {
    clearMutation.mutate(undefined, { onSuccess: () => void refresh() });
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={1}>Batch</Title>
          <Text c="dimmed">Sequenzielle Review- und Apply-Verarbeitung für ausgewählte Künstler und Alben.</Text>
        </div>
        <Group>
          <StatusPill value={Boolean(batch?.running)} />
          <Button leftSection={<RefreshCw size={16} />} variant="subtle" onClick={() => void refresh()}>
            Refresh
          </Button>
          <Button leftSection={<Ban size={16} />} color="red" variant="light" loading={cancelMutation.isPending} onClick={cancel}>
            Cancel
          </Button>
          <Button leftSection={<Trash2 size={16} />} variant="light" loading={clearMutation.isPending} onClick={clear}>
            Leeren
          </Button>
        </Group>
      </Group>

      {status.isLoading ? <Skeleton h={180} /> : null}
      {status.error ? <Alert color="red">{status.error.message}</Alert> : null}

      {batch ? (
        <section className="surface">
          <Group justify="space-between" align="flex-start">
            <div>
              <Title order={2}>Queue</Title>
              <Text c="dimmed" size="sm">
                {batch.running ? "Batch läuft" : "Batch bereit"} · {batch.pending} wartend · {batch.completed} abgeschlossen · {batch.failed} Fehler
              </Text>
            </div>
            <Badge variant="light">{batch.progress}%</Badge>
          </Group>
          <Progress value={batch.progress} animated={batch.running} mt="md" />
          <Group grow mt="md">
            <Metric label="Aktiv" value={batch.active?.name ?? "keins"} />
            <Metric label="Gesamt" value={batch.total.toLocaleString("de-DE")} />
            <Metric label="Restzeit" value={formatSeconds(batch.estimatedRemainingSeconds)} />
          </Group>
          {batch.message ? <Alert mt="md">{batch.message}</Alert> : null}
          <BatchTable items={batch.queue} empty="Keine Einträge in der Queue." />
        </section>
      ) : null}

      <section className="surface">
        <Group justify="space-between">
          <Title order={2}>Historie</Title>
          <Button leftSection={<RotateCcw size={16} />} variant="subtle" onClick={() => void refresh()}>
            Neu laden
          </Button>
        </Group>
        {history.isLoading ? <Skeleton h={120} mt="md" /> : null}
        {history.error ? <Alert color="red">{history.error.message}</Alert> : null}
        <BatchTable items={history.data?.history ?? []} empty="Noch keine Batch-Historie vorhanden." />
      </section>
    </Stack>
  );
}

function BatchTable({ items, empty }: { items: BatchQueueItem[]; empty: string }) {
  return (
    <Table mt="md">
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Typ</Table.Th>
          <Table.Th>Name</Table.Th>
          <Table.Th>Status</Table.Th>
          <Table.Th>Fortschritt</Table.Th>
          <Table.Th>Laufzeit</Table.Th>
          <Table.Th>Fehler</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {items.map((item) => (
          <Table.Tr key={item.id}>
            <Table.Td>{item.target === "artist" ? "Künstler" : "Album"}</Table.Td>
            <Table.Td>{item.name}</Table.Td>
            <Table.Td>
              <StatusBadge status={item.status} />
            </Table.Td>
            <Table.Td>{item.progress}%</Table.Td>
            <Table.Td>{formatSeconds(item.runtimeSeconds)}</Table.Td>
            <Table.Td>{item.error ?? "n/a"}</Table.Td>
          </Table.Tr>
        ))}
        {!items.length ? (
          <Table.Tr>
            <Table.Td colSpan={6}>
              <Text c="dimmed">{empty}</Text>
            </Table.Td>
          </Table.Tr>
        ) : null}
      </Table.Tbody>
    </Table>
  );
}

function StatusBadge({ status }: { status: BatchQueueItem["status"] }) {
  const color = status === "completed" ? "teal" : status === "failed" ? "red" : status === "running" ? "blue" : status === "skipped" ? "gray" : "yellow";
  return <Badge color={color}>{status}</Badge>;
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

function formatSeconds(value?: number | null) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  if (value < 60) {
    return `${Math.round(value)} s`;
  }
  return `${Math.round(value / 60)} min`;
}
