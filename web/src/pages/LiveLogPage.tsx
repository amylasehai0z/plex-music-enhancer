import { Button, Group, NativeSelect, Stack, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Copy, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { MonacoPanel } from "../components/MonacoPanel";
import { useDebugMeta, useDebugPrompt, useDebugReview } from "../hooks/useApi";

const levels = ["ALL", "DEBUG", "INFO", "WARNING", "ERROR"];

export function LiveLogPage() {
  const [level, setLevel] = useState("ALL");
  const [search, setSearch] = useState("");
  const prompt = useDebugPrompt();
  const meta = useDebugMeta();
  const review = useDebugReview();

  const content = useMemo(() => {
    const sections = [
      "=== REVIEW LOG ===",
      review.data?.content ?? "",
      "=== PROMPT META ===",
      JSON.stringify(meta.data?.payload ?? {}, null, 2),
      "=== PROMPT ===",
      prompt.data?.content ?? "",
    ];
    return sections
      .join("\n\n")
      .split("\n")
      .filter((line) => (level === "ALL" ? true : line.toUpperCase().includes(level)))
      .filter((line) => (search ? line.toLowerCase().includes(search.toLowerCase()) : true))
      .join("\n");
  }, [level, meta.data?.payload, prompt.data?.content, review.data?.content, search]);

  function refresh() {
    void prompt.refetch();
    void meta.refetch();
    void review.refetch();
  }

  useEffect(() => {
    const interval = window.setInterval(refresh, 5000);
    return () => window.clearInterval(interval);
  });

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <div>
          <Title order={1}>Live Log</Title>
          <Text c="dimmed">Aktualisierte Backend-Debugausgaben aus vorhandenen REST-Endpunkten.</Text>
        </div>
        <Group>
          <Button leftSection={<RefreshCw size={16} />} variant="light" onClick={refresh}>
            Refresh
          </Button>
          <Button
            leftSection={<Copy size={16} />}
            variant="subtle"
            onClick={() => {
              void navigator.clipboard.writeText(content);
              notifications.show({ color: "teal", message: "Log kopiert." });
            }}
          >
            Copy
          </Button>
        </Group>
      </Group>
      <section className="surface">
        <Group grow>
          <NativeSelect label="Level" data={levels} value={level} onChange={(event) => setLevel(event.currentTarget.value)} />
          <TextInput label="Suche" value={search} onChange={(event) => setSearch(event.currentTarget.value)} />
        </Group>
      </section>
      <MonacoPanel title="Backend Log Stream" value={content} language="log" height={620} />
    </Stack>
  );
}
