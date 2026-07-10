import { Button, Grid, JsonInput, Stack, Tabs, Table, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../api/client";

export function SettingsPage() {
  const config = useQuery({ queryKey: ["configuration"], queryFn: () => api.config.get() });
  const [value, setValue] = useState("{}");
  const update = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.config.update(payload),
    onSuccess: () => notifications.show({ color: "teal", message: "Konfiguration geprüft." }),
    onError: (error) => notifications.show({ color: "red", message: error.message }),
  });

  useEffect(() => {
    if (config.data) {
      setValue(JSON.stringify(config.data.configuration, null, 2));
    }
  }, [config.data]);

  return (
    <Stack gap="md">
      <div>
        <Title order={1}>Einstellungen</Title>
        <Text c="dimmed">Sanitisierte Konfiguration aus der REST-API.</Text>
      </div>
      <Grid>
        <Grid.Col span={{ base: 12, lg: 8 }}>
          <Tabs defaultValue="provider">
            <Tabs.List>
              <Tabs.Tab value="provider">Provider</Tabs.Tab>
              <Tabs.Tab value="plex">Plex</Tabs.Tab>
              <Tabs.Tab value="prompt">Prompt</Tabs.Tab>
              <Tabs.Tab value="cache">Cache</Tabs.Tab>
              <Tabs.Tab value="review">Review</Tabs.Tab>
              <Tabs.Tab value="debug">Debug</Tabs.Tab>
              <Tabs.Tab value="server">Server</Tabs.Tab>
              <Tabs.Tab value="json">JSON</Tabs.Tab>
            </Tabs.List>
            {["provider", "plex", "prompt", "cache", "review", "debug", "server"].map((section) => (
              <Tabs.Panel key={section} value={section} pt="md">
                <section className="surface">
                  <Title order={2}>{sectionLabel(section)}</Title>
                  <ConfigurationTable configuration={config.data?.configuration ?? {}} section={section} />
                </section>
              </Tabs.Panel>
            ))}
            <Tabs.Panel value="json" pt="md">
              <JsonInput
                value={value}
                onChange={setValue}
                minRows={20}
                autosize
                formatOnBlur
                validationError="Ungültiges JSON"
              />
            </Tabs.Panel>
          </Tabs>
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 4 }}>
          <section className="surface">
            <Title order={2}>Hinweis</Title>
            <Text size="sm" c="dimmed">
              Persistente Konfigurationsänderungen werden vom Backend vorbereitet. Diese Ansicht
              spricht ausschließlich mit der REST-API.
            </Text>
            <Button
              mt="md"
              onClick={() => update.mutate(JSON.parse(value) as Record<string, unknown>)}
              loading={update.isPending}
            >
              Über REST-API prüfen
            </Button>
          </section>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}

function ConfigurationTable({
  configuration,
  section,
}: {
  configuration: Record<string, unknown>;
  section: string;
}) {
  const entries = Object.entries(configuration).filter(([key]) => sectionKeys[section]?.some((part) => key.toLowerCase().includes(part)));
  const visibleEntries = entries.length ? entries : Object.entries(configuration).slice(0, 8);

  return (
    <Table mt="md">
      <Table.Tbody>
        {visibleEntries.map(([key, entryValue]) => (
          <Table.Tr key={key}>
            <Table.Td>{key}</Table.Td>
            <Table.Td>{formatSettingValue(entryValue)}</Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}

const sectionKeys: Record<string, string[]> = {
  provider: ["provider", "model", "openai", "discogs", "lastfm"],
  plex: ["plex"],
  prompt: ["prompt"],
  cache: ["cache"],
  review: ["review", "quality", "verification"],
  debug: ["debug", "log"],
  server: ["web", "server", "port", "host"],
};

function sectionLabel(section: string) {
  return {
    provider: "Provider und Modell",
    plex: "Plex",
    prompt: "Prompt",
    cache: "Cache",
    review: "Review",
    debug: "Debug",
    server: "Server",
  }[section];
}

function formatSettingValue(value: unknown) {
  if (typeof value === "boolean") {
    return value ? "Ja" : "Nein";
  }
  if (value === null || value === undefined || value === "") {
    return "nicht gesetzt";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}
