import { Badge, Group, ScrollArea, Stack, Text, Timeline, Title } from "@mantine/core";
import { AlertTriangle, CheckCircle2, Clock3, Info } from "lucide-react";

import { useDashboardData, useDebugReview } from "../hooks/useApi";

export function ActivityPanel({ compact = false }: { compact?: boolean }) {
  const { statistics, providers, configuration } = useDashboardData();
  const review = useDebugReview();
  const plexConfigured = Boolean(configuration.data?.configuration.plexConfigured);
  const provider = providers.data?.find((item) => item.details.type === "ai");
  const reviewSections = Object.keys(review.data?.sections ?? {});

  const items = [
    {
      title: "Plex Verbindung",
      detail: plexConfigured ? "Konfiguriert" : "Konfiguration offen",
      ok: plexConfigured,
    },
    {
      title: "AI Provider",
      detail: provider ? `${provider.name} · ${provider.model ?? "Modell offen"}` : "Nicht geladen",
      ok: Boolean(provider?.configured),
    },
    {
      title: "Cache",
      detail: `${statistics.data?.cacheEntries ?? 0} Einträge`,
      ok: true,
    },
    {
      title: "Letzter Review-Log",
      detail: review.data?.exists ? `${reviewSections.length} Abschnitte verfügbar` : "Noch kein Review-Log",
      ok: Boolean(review.data?.exists),
    },
  ];

  return (
    <aside className="activity-panel">
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={3}>Aktivität</Title>
          <Badge color="teal" variant="light">
            Live
          </Badge>
        </Group>
        <ScrollArea h={compact ? 220 : "calc(100vh - 150px)"} type="hover">
          <Timeline active={items.length - 1} bulletSize={22} lineWidth={2}>
            {items.map((item) => (
              <Timeline.Item
                key={item.title}
                title={item.title}
                bullet={item.ok ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
                color={item.ok ? "teal" : "yellow"}
              >
                <Text size="xs" c="dimmed">
                  {item.detail}
                </Text>
              </Timeline.Item>
            ))}
          </Timeline>
          <Stack gap="xs" mt="lg">
            <Group gap="xs">
              <Clock3 size={14} />
              <Text size="sm" fw={700}>
                Laufende Reviews
              </Text>
            </Group>
            <Text size="xs" c="dimmed">
              Keine laufenden Reviews über vorhandene REST-Daten gemeldet.
            </Text>
            <Group gap="xs" mt="sm">
              <Info size={14} />
              <Text size="sm" fw={700}>
                Hinweise
              </Text>
            </Group>
            <Text size="xs" c="dimmed">
              Die Aktivitätskarte liest vorhandene Status-, Provider- und Debug-Endpunkte.
            </Text>
          </Stack>
        </ScrollArea>
      </Stack>
    </aside>
  );
}
