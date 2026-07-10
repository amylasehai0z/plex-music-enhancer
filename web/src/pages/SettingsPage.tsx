import {
  Alert,
  Badge,
  Button,
  Grid,
  Group,
  JsonInput,
  PasswordInput,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import type { Configuration, ConfigurationUpdateRequest } from "../types/api";

const EMPTY_FORM: SettingsFormState = {
  aiProvider: "dummy",
  aiModel: "gpt-5.5",
  openaiApiKey: "",
  plexUrl: "",
  plexToken: "",
  discogsToken: "",
  lastfmApiKey: "",
};

export function SettingsPage() {
  const queryClient = useQueryClient();
  const config = useQuery({ queryKey: ["configuration"], queryFn: () => api.config.get() });
  const configuration = config.data?.configuration;
  const [form, setForm] = useState<SettingsFormState>(EMPTY_FORM);
  const [jsonValue, setJsonValue] = useState("{}");
  const [plexStatus, setPlexStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!configuration) {
      return;
    }
    setForm({
      aiProvider: configuration.aiProvider || "dummy",
      aiModel: configuration.aiModel || "gpt-5.5",
      openaiApiKey: "",
      plexUrl: configuration.plexUrl ?? "",
      plexToken: "",
      discogsToken: "",
      lastfmApiKey: "",
    });
    setJsonValue(JSON.stringify(configuration, null, 2));
  }, [configuration]);

  const save = useMutation({
    mutationFn: (payload: ConfigurationUpdateRequest) => api.config.update(payload),
    onSuccess: async (response) => {
      notifications.show({ color: "teal", message: "Konfiguration gespeichert." });
      setJsonValue(JSON.stringify(response.configuration, null, 2));
      await queryClient.invalidateQueries({ queryKey: ["configuration"] });
      await queryClient.invalidateQueries({ queryKey: ["providers"] });
    },
    onError: (error) => notifications.show({ color: "red", message: error.message }),
  });

  const plexTest = useMutation({
    mutationFn: (payload: ConfigurationUpdateRequest) => api.config.testPlex(payload),
    onSuccess: (response) => {
      const serverName = response.serverName ? ` (${response.serverName})` : "";
      setPlexStatus(`${response.message}${serverName}`);
      notifications.show({
        color: response.ok ? "teal" : "yellow",
        message: response.ok ? "Plex-Verbindung erfolgreich." : response.message,
      });
    },
    onError: (error) => {
      setPlexStatus(error.message);
      notifications.show({ color: "red", message: error.message });
    },
  });

  const sanitizedJson = useMemo(
    () => JSON.stringify(configuration ?? {}, null, 2),
    [configuration],
  );

  return (
    <Stack gap="md">
      <div>
        <Title order={1}>Einstellungen</Title>
        <Text c="dimmed">Persistente Runtime-Konfiguration aus dem Docker-Config-Volume.</Text>
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

            <Tabs.Panel value="provider" pt="md">
              <section className="surface">
                <Title order={2}>Provider</Title>
                <ProviderSettings
                  configuration={configuration}
                  form={form}
                  loading={save.isPending}
                  onChange={setForm}
                  onSave={() => save.mutate(providerPayload(form))}
                />
              </section>
            </Tabs.Panel>

            <Tabs.Panel value="plex" pt="md">
              <section className="surface">
                <Title order={2}>Plex</Title>
                <PlexSettings
                  configuration={configuration}
                  form={form}
                  loading={save.isPending}
                  testing={plexTest.isPending}
                  status={plexStatus}
                  onChange={setForm}
                  onSave={() => save.mutate(plexPayload(form))}
                  onTest={() => plexTest.mutate(plexPayload(form))}
                />
              </section>
            </Tabs.Panel>

            {["prompt", "cache", "review", "debug", "server"].map((section) => (
              <Tabs.Panel key={section} value={section} pt="md">
                <section className="surface">
                  <Title order={2}>{sectionLabel(section)}</Title>
                  <ConfigurationTable configuration={configuration ?? {}} section={section} />
                </section>
              </Tabs.Panel>
            ))}

            <Tabs.Panel value="json" pt="md">
              <JsonInput
                label="Sanitisierte Konfiguration"
                value={jsonValue}
                onChange={setJsonValue}
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
            <Title order={2}>Sicherheit</Title>
            <Stack gap="sm" mt="md">
              <SecretStatus
                label="OpenAI API Key"
                configured={Boolean(configuration?.openaiApiKeyConfigured)}
                masked={configuration?.openaiApiKeyMasked}
              />
              <SecretStatus
                label="Plex Token"
                configured={Boolean(configuration?.plexTokenConfigured)}
                masked={configuration?.plexTokenMasked}
              />
              <SecretStatus
                label="Discogs Token"
                configured={Boolean(configuration?.discogsConfigured)}
                masked={configuration?.discogsTokenMasked}
              />
              <SecretStatus
                label="Last.fm API Key"
                configured={Boolean(configuration?.lastfmConfigured)}
                masked={configuration?.lastfmApiKeyMasked}
              />
            </Stack>
            <Text size="sm" c="dimmed" mt="md">
              Secrets werden nicht aus der API zurückgegeben. Neue Werte werden nur beim Speichern
              übertragen und danach wieder aus den Eingabefeldern entfernt.
            </Text>
            <Button
              variant="light"
              mt="md"
              onClick={() => setJsonValue(sanitizedJson)}
              disabled={!configuration}
            >
              JSON aktualisieren
            </Button>
          </section>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}

function ProviderSettings({
  configuration,
  form,
  loading,
  onChange,
  onSave,
}: {
  configuration?: Configuration;
  form: SettingsFormState;
  loading: boolean;
  onChange: (value: SettingsFormState) => void;
  onSave: () => void;
}) {
  return (
    <Stack gap="md" mt="md">
      <Group align="flex-end" grow>
        <Select
          label="AI Provider"
          data={[
            { value: "dummy", label: "Dummy" },
            { value: "openai", label: "OpenAI" },
            { value: "ollama", label: "Ollama" },
          ]}
          value={form.aiProvider}
          onChange={(value) => onChange({ ...form, aiProvider: value ?? "dummy" })}
        />
        <TextInput
          label="AI Modell"
          value={form.aiModel}
          onChange={(event) => onChange({ ...form, aiModel: event.currentTarget.value })}
          placeholder="gpt-5.5"
        />
      </Group>
      <PasswordInput
        label="OpenAI API Key"
        value={form.openaiApiKey}
        onChange={(event) => onChange({ ...form, openaiApiKey: event.currentTarget.value })}
        placeholder={configuration?.openaiApiKeyConfigured ? "Neuen API Key eingeben" : "Nicht konfiguriert"}
      />
      <Group align="flex-end" grow>
        <PasswordInput
          label="Discogs Token"
          value={form.discogsToken}
          onChange={(event) => onChange({ ...form, discogsToken: event.currentTarget.value })}
          placeholder={configuration?.discogsConfigured ? "Neuen Token eingeben" : "Nicht konfiguriert"}
        />
        <PasswordInput
          label="Last.fm API Key"
          value={form.lastfmApiKey}
          onChange={(event) => onChange({ ...form, lastfmApiKey: event.currentTarget.value })}
          placeholder={configuration?.lastfmConfigured ? "Neuen API Key eingeben" : "Nicht konfiguriert"}
        />
      </Group>
      <Group justify="space-between">
        <Group gap="xs">
          <SecretBadge configured={Boolean(configuration?.openaiApiKeyConfigured)} />
          <Text size="sm" c="dimmed">
            Aktiver Provider: {configuration?.aiProvider ?? "nicht geladen"}
          </Text>
        </Group>
        <Button onClick={onSave} loading={loading}>
          Provider speichern
        </Button>
      </Group>
    </Stack>
  );
}

function PlexSettings({
  configuration,
  form,
  loading,
  testing,
  status,
  onChange,
  onSave,
  onTest,
}: {
  configuration?: Configuration;
  form: SettingsFormState;
  loading: boolean;
  testing: boolean;
  status: string | null;
  onChange: (value: SettingsFormState) => void;
  onSave: () => void;
  onTest: () => void;
}) {
  return (
    <Stack gap="md" mt="md">
      <TextInput
        label="Plex URL"
        value={form.plexUrl}
        onChange={(event) => onChange({ ...form, plexUrl: event.currentTarget.value })}
        placeholder="http://plex:32400"
      />
      <PasswordInput
        label="Plex Token"
        value={form.plexToken}
        onChange={(event) => onChange({ ...form, plexToken: event.currentTarget.value })}
        placeholder={configuration?.plexTokenConfigured ? "Neuen Token eingeben" : "Nicht konfiguriert"}
      />
      {status ? (
        <Alert color={status.toLowerCase().includes("success") ? "teal" : "blue"}>{status}</Alert>
      ) : null}
      <Group justify="space-between">
        <Group gap="xs">
          <SecretBadge configured={Boolean(configuration?.plexTokenConfigured)} />
          <Text size="sm" c="dimmed">
            Status: {configuration?.plexConfigured ? "Plex konfiguriert" : "Plex nicht konfiguriert"}
          </Text>
        </Group>
        <Group>
          <Button variant="light" onClick={onTest} loading={testing}>
            Verbindung testen
          </Button>
          <Button onClick={onSave} loading={loading}>
            Plex speichern
          </Button>
        </Group>
      </Group>
    </Stack>
  );
}

function SecretStatus({
  label,
  configured,
  masked,
}: {
  label: string;
  configured: boolean;
  masked?: string | null;
}) {
  return (
    <Group justify="space-between" wrap="nowrap">
      <div>
        <Text size="sm" fw={700}>
          {label}
        </Text>
        <Text size="xs" c="dimmed">
          {masked ?? "kein Wert gespeichert"}
        </Text>
      </div>
      <SecretBadge configured={configured} />
    </Group>
  );
}

function SecretBadge({ configured }: { configured: boolean }) {
  return (
    <Badge color={configured ? "teal" : "gray"} variant="light">
      {configured ? "konfiguriert" : "nicht konfiguriert"}
    </Badge>
  );
}

function ConfigurationTable({
  configuration,
  section,
}: {
  configuration: Record<string, unknown>;
  section: string;
}) {
  const entries = Object.entries(configuration).filter(([key]) =>
    sectionKeys[section]?.some((part) => key.toLowerCase().includes(part)),
  );
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

function providerPayload(form: SettingsFormState): ConfigurationUpdateRequest {
  return compactPayload({
    aiProvider: form.aiProvider,
    aiModel: form.aiModel,
    openaiApiKey: form.openaiApiKey,
    discogsToken: form.discogsToken,
    lastfmApiKey: form.lastfmApiKey,
  });
}

function plexPayload(form: SettingsFormState): ConfigurationUpdateRequest {
  return compactPayload({
    plexUrl: form.plexUrl,
    plexToken: form.plexToken,
  });
}

function compactPayload(payload: ConfigurationUpdateRequest): ConfigurationUpdateRequest {
  return Object.fromEntries(
    Object.entries(payload).filter(([, value]) => value !== ""),
  ) as ConfigurationUpdateRequest;
}

const sectionKeys: Record<string, string[]> = {
  prompt: ["prompt"],
  cache: ["cache"],
  review: ["review", "quality", "verification"],
  debug: ["debug", "log"],
  server: ["web", "server", "port", "host"],
};

function sectionLabel(section: string) {
  return {
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

interface SettingsFormState {
  aiProvider: string;
  aiModel: string;
  openaiApiKey: string;
  plexUrl: string;
  plexToken: string;
  discogsToken: string;
  lastfmApiKey: string;
}
