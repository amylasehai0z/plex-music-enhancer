import { Grid, Group, Skeleton, Stack, Table, Text, Title } from "@mantine/core";
import { Album, ClipboardCheck, Cpu, Database, Library, Server, UserRound } from "lucide-react";

import { MetricCard } from "../components/MetricCard";
import { StatusPill } from "../components/StatusPill";
import { useDashboardData, useDebugReview } from "../hooks/useApi";
import { formatNumber } from "../utils/format";

export function DashboardPage() {
  const { statistics, providers, configuration, version } = useDashboardData();
  const reviewLog = useDebugReview();
  const stats = statistics.data;
  const config = configuration.data?.configuration;
  const provider = providers.data?.find((item) => item.details.type === "ai");
  const reviewSections = Object.keys(reviewLog.data?.sections ?? {});
  const userAgentData = navigator as Navigator & { userAgentData?: { platform?: string } };

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
            <MetricCard label="Reviews" value={formatNumber(reviewLog.data?.exists ? 1 : 0)} icon={ClipboardCheck} />
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
            <Title order={2}>System</Title>
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
          <section className="surface">
            <Title order={2}>Letzte Aktivität</Title>
            <Table>
              <Table.Tbody>
                <Table.Tr>
                  <Table.Td>Letzter Review</Table.Td>
                  <Table.Td>{reviewLog.data?.exists ? "Debug-Log vorhanden" : "Noch keiner"}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>Review-Abschnitte</Table.Td>
                  <Table.Td>{reviewSections.length}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>Letzte Änderungen</Table.Td>
                  <Table.Td>Über vorhandene API nicht versioniert</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>Fehler / Warnungen</Table.Td>
                  <Table.Td>{reviewLog.isError ? "Debug-Log nicht erreichbar" : "Keine gemeldet"}</Table.Td>
                </Table.Tr>
              </Table.Tbody>
            </Table>
          </section>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
