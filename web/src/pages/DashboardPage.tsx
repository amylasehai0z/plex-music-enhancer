import { Alert, Button, Grid, Group, Progress, Skeleton, Stack, Table, Text, Title } from "@mantine/core";
import { useQueryClient } from "@tanstack/react-query";
import { Album, ClipboardCheck, Cpu, Database, Library, RefreshCw, Server, Star, UserRound } from "lucide-react";

import { ActivityPanel } from "../components/ActivityPanel";
import { MetricCard } from "../components/MetricCard";
import { StatusPill } from "../components/StatusPill";
import { useDashboardData, usePlexSyncMutation } from "../hooks/useApi";
import { formatNumber } from "../utils/format";

export function DashboardPage() {
  const queryClient = useQueryClient();
  const { statistics, providers, configuration, version, plexSync } = useDashboardData();
  const syncMutation = usePlexSyncMutation();
  const stats = statistics.data;
  const config = configuration.data?.configuration;
  const sync = plexSync.data;
  const provider = providers.data?.find((item) => item.details.type === "ai");
  const userAgentData = navigator as Navigator & { userAgentData?: { platform?: string } };
  const syncRunning = Boolean(sync?.running || syncMutation.isPending);

  const startSync = () => {
    syncMutation.mutate(undefined, {
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["plex", "sync"] });
        await queryClient.invalidateQueries({ queryKey: ["statistics"] });
      },
    });
  };

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <div>
          <Title order={1}>Dashboard</Title>
          <Text c="dimmed">Status, Provider und Review-Kennzahlen.</Text>
        </div>
        <StatusPill value={statistics.isSuccess && providers.isSuccess} />
      </Group>
      {statistics.isLoading ? (
        <Skeleton h={120} />
      ) : (
        <Grid>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <MetricCard label="Künstler" value={formatNumber(stats?.artists)} icon={UserRound} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <MetricCard label="Alben" value={formatNumber(stats?.albums)} icon={Album} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <MetricCard label="Bibliotheken" value={formatNumber(stats?.libraries)} icon={Library} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <MetricCard label="Cache" value={formatNumber(stats?.cacheEntries)} icon={Database} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <MetricCard label="Reviews" value={formatNumber(stats?.reviews)} icon={ClipboardCheck} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <MetricCard
              label="Ø Bewertung"
              value={stats?.averageRating !== null && stats?.averageRating !== undefined ? `${stats.averageRating}` : "n/a"}
              icon={Star}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <MetricCard label="Provider" value={formatNumber(providers.data?.length)} icon={Server} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <MetricCard label="API" value={version.data?.apiVersion ?? "n/a"} icon={Cpu} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <MetricCard label="App" value={version.data?.version ?? "n/a"} icon={Library} />
          </Grid.Col>
        </Grid>
      )}
      <Grid>
        <Grid.Col span={{ base: 12, lg: 6 }}>
          <section className="surface">
            <Group justify="space-between" align="flex-start">
              <div>
                <Title order={2}>Plex Synchronisation</Title>
                <Text c="dimmed" size="sm">
                  Musikbibliotheken aus Plex lokal erfassen.
                </Text>
              </div>
              <StatusPill value={Boolean(sync?.lastSync) && !sync?.error} />
            </Group>
            <Stack gap="sm" mt="md">
              <Group grow>
                <MetricCard label="Artists" value={formatNumber(sync?.artists)} icon={UserRound} />
                <MetricCard label="Alben" value={formatNumber(sync?.albums)} icon={Album} />
                <MetricCard label="Tracks" value={formatNumber(sync?.tracks)} icon={Library} />
              </Group>
              <Progress value={sync?.progress ?? 0} animated={syncRunning} />
              <Table>
                <Table.Tbody>
                  <Table.Tr>
                    <Table.Td>Status</Table.Td>
                    <Table.Td>{syncRunning ? "Synchronisation läuft" : "Bereit"}</Table.Td>
                  </Table.Tr>
                  <Table.Tr>
                    <Table.Td>Fortschritt</Table.Td>
                    <Table.Td>{sync?.progress ?? 0}%</Table.Td>
                  </Table.Tr>
                  <Table.Tr>
                    <Table.Td>Letzter Sync</Table.Td>
                    <Table.Td>{formatSyncDate(sync?.lastSync)}</Table.Td>
                  </Table.Tr>
                </Table.Tbody>
              </Table>
              {sync?.error || syncMutation.error ? (
                <Alert color="red">
                  {sync?.error ?? syncMutation.error?.message ?? "Synchronisation fehlgeschlagen."}
                </Alert>
              ) : null}
              <Button
                leftSection={<RefreshCw size={16} />}
                onClick={startSync}
                loading={syncRunning}
                disabled={!config?.plexConfigured}
              >
                Synchronisieren
              </Button>
            </Stack>
          </section>
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 6 }}>
          <section className="surface">
            <Title order={2}>Systemstatus</Title>
            <Table>
              <Table.Tbody>
                <Table.Tr>
                  <Table.Td>Plex-Verbindung</Table.Td>
                  <Table.Td>
                    <StatusPill value={Boolean(config?.plexConfigured)} />
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>AI-Provider</Table.Td>
                  <Table.Td>{provider?.name ?? "unbekannt"}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>Modell</Table.Td>
                  <Table.Td>{provider?.model ?? "nicht gesetzt"}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>Plex Music Enhancer</Table.Td>
                  <Table.Td>{version.data?.version ?? "nicht geladen"}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>API-Version</Table.Td>
                  <Table.Td>{version.data?.apiVersion ?? "nicht geladen"}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>Betriebssystem</Table.Td>
                  <Table.Td>{navigator.platform || "nicht verfügbar"}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>CPU Architektur</Table.Td>
                  <Table.Td>{userAgentData.userAgentData?.platform ?? navigator.platform ?? "nicht verfügbar"}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>Python / FastAPI / RAM</Table.Td>
                  <Table.Td>Vom aktuellen REST-Vertrag nicht bereitgestellt</Table.Td>
                </Table.Tr>
              </Table.Tbody>
            </Table>
          </section>
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 6 }}>
          <section className="surface activity-footer-card">
            <ActivityPanel compact />
          </section>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}

function formatSyncDate(value?: string | null) {
  if (!value) {
    return "Noch nie";
  }
  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
