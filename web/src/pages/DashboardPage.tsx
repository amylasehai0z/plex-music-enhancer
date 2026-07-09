import { Grid, Group, Skeleton, Stack, Table, Text, Title } from "@mantine/core";
import { Album, Database, Library, UserRound } from "lucide-react";

import { MetricCard } from "../components/MetricCard";
import { StatusPill } from "../components/StatusPill";
import { useDashboardData } from "../hooks/useApi";
import { formatNumber } from "../utils/format";

export function DashboardPage() {
  const { statistics, providers, configuration } = useDashboardData();
  const stats = statistics.data;
  const config = configuration.data?.configuration ?? {};
  const provider = providers.data?.find((item) => item.details.type === "ai");

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
                    <StatusPill value={Boolean(config.plexConfigured)} />
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
              </Table.Tbody>
            </Table>
          </section>
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 6 }}>
          <section className="surface">
            <Title order={2}>Qualität</Title>
            <Table>
              <Table.Tbody>
                <Table.Tr>
                  <Table.Td>Prompt Efficiency Durchschnitt</Table.Td>
                  <Table.Td>Wird nach Reviews berechnet</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>Editorial Score Durchschnitt</Table.Td>
                  <Table.Td>Wird nach Reviews berechnet</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>QA Durchschnitt</Table.Td>
                  <Table.Td>Wird nach Reviews berechnet</Table.Td>
                </Table.Tr>
              </Table.Tbody>
            </Table>
          </section>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
