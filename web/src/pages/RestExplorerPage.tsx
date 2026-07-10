import { Badge, Button, Grid, Group, JsonInput, NativeSelect, Stack, Table, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Play, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";

import { api, ApiError } from "../api/client";
import { MonacoPanel } from "../components/MonacoPanel";

const endpoints = [
  { method: "GET", path: "/system/health", label: "Health" },
  { method: "GET", path: "/system/version", label: "Version" },
  { method: "GET", path: "/statistics", label: "Statistics" },
  { method: "GET", path: "/providers", label: "Providers" },
  { method: "GET", path: "/config", label: "Configuration" },
  { method: "GET", path: "/artists", label: "Artists" },
  { method: "GET", path: "/albums", label: "Albums" },
  { method: "GET", path: "/reviews", label: "Album Reviews" },
  { method: "GET", path: "/reviews/200", label: "Album Review Detail" },
  { method: "GET", path: "/debug/prompt", label: "Debug Prompt" },
  { method: "GET", path: "/debug/meta", label: "Debug Meta" },
  { method: "GET", path: "/debug/review", label: "Debug Review" },
  { method: "GET", path: "/debug/explain", label: "Explain" },
  { method: "POST", path: "/preview", label: "Preview" },
  { method: "POST", path: "/review/album", label: "Review Album" },
  { method: "POST", path: "/review/artist", label: "Review Artist" },
  { method: "POST", path: "/reviews/generate/200", label: "Generate Album Review" },
  { method: "POST", path: "/apply", label: "Apply" },
];

export function RestExplorerPage() {
  const [endpoint, setEndpoint] = useState(endpoints[0].path);
  const [body, setBody] = useState("{\n  \"target\": \"album\",\n  \"artist\": \"Jennifer Rush\",\n  \"album\": \"Credo\"\n}");
  const [response, setResponse] = useState("{}");
  const [status, setStatus] = useState<number | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const selected = useMemo(() => endpoints.find((item) => item.path === endpoint) ?? endpoints[0], [endpoint]);

  async function execute() {
    const started = performance.now();
    try {
      const payload =
        selected.method === "GET"
          ? await api.client.get<unknown>(selected.path)
          : await api.client.post<unknown>(selected.path, JSON.parse(body) as unknown);
      setStatus(200);
      setResponse(JSON.stringify(payload, null, 2));
    } catch (error) {
      if (error instanceof ApiError) {
        setStatus(error.status);
        setResponse(JSON.stringify(error.payload, null, 2));
      } else {
        setStatus(0);
        setResponse(JSON.stringify({ message: String(error) }, null, 2));
      }
      notifications.show({ color: "red", message: "REST-Aufruf fehlgeschlagen." });
    } finally {
      setDuration(Math.round(performance.now() - started));
    }
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <div>
          <Title order={1}>REST Explorer</Title>
          <Text c="dimmed">Vorhandene API-Endpunkte inspizieren und Debug-Antworten prüfen.</Text>
        </div>
        <Button leftSection={<Play size={16} />} onClick={() => void execute()}>
          Request senden
        </Button>
      </Group>
      <Grid>
        <Grid.Col span={{ base: 12, xl: 4 }}>
          <section className="surface">
            <Group justify="space-between" mb="md">
              <Title order={2}>Endpunkte</Title>
              <Button leftSection={<RefreshCw size={14} />} size="xs" variant="subtle" onClick={() => setResponse("{}")}>
                Reset
              </Button>
            </Group>
            <NativeSelect
              label="Endpoint"
              data={endpoints.map((item) => ({ value: item.path, label: `${item.method} ${item.path}` }))}
              value={endpoint}
              onChange={(event) => setEndpoint(event.currentTarget.value)}
            />
            <Table mt="md">
              <Table.Tbody>
                <Table.Tr>
                  <Table.Td>Methode</Table.Td>
                  <Table.Td><Badge>{selected.method}</Badge></Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>Status</Table.Td>
                  <Table.Td>{status ?? "n/a"}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>Response Time</Table.Td>
                  <Table.Td>{duration !== null ? `${duration} ms` : "n/a"}</Table.Td>
                </Table.Tr>
              </Table.Tbody>
            </Table>
            {selected.method !== "GET" ? (
              <JsonInput
                mt="md"
                label="Request JSON"
                value={body}
                onChange={setBody}
                minRows={8}
                autosize
                formatOnBlur
              />
            ) : null}
          </section>
        </Grid.Col>
        <Grid.Col span={{ base: 12, xl: 8 }}>
          <MonacoPanel title="Response JSON" value={response} language="json" height={650} />
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
