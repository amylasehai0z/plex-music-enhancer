import { Button, Group, Tabs, Text, Title } from "@mantine/core";
import { Copy, Download, RefreshCw } from "lucide-react";

import { MonacoPanel } from "../components/MonacoPanel";
import { usePromptLog, useReviewLog } from "../hooks/useApi";

export function PromptDebugPage() {
  const prompt = usePromptLog();
  const review = useReviewLog();

  function download(filename: string, content: string) {
    const url = URL.createObjectURL(new Blob([content], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={1}>Prompt Debug</Title>
          <Text c="dimmed">Temporäre Debug-Dateien aus dem Backend.</Text>
        </div>
        <Group>
          <Button leftSection={<RefreshCw size={16} />} variant="light" onClick={() => void prompt.refetch()}>
            Refresh
          </Button>
          <Button
            leftSection={<Copy size={16} />}
            variant="subtle"
            onClick={() => void navigator.clipboard.writeText(prompt.data?.content ?? "")}
          >
            Copy
          </Button>
          <Button
            leftSection={<Download size={16} />}
            variant="subtle"
            onClick={() => download("openai_prompt.txt", prompt.data?.content ?? "")}
          >
            Download
          </Button>
        </Group>
      </Group>
      <Tabs defaultValue="prompt">
        <Tabs.List>
          <Tabs.Tab value="prompt">Prompt</Tabs.Tab>
          <Tabs.Tab value="meta">Prompt Meta</Tabs.Tab>
          <Tabs.Tab value="review">Review Log</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="prompt" pt="md">
          <MonacoPanel title={prompt.data?.path ?? "/tmp/openai_prompt.txt"} value={prompt.data?.content} />
        </Tabs.Panel>
        <Tabs.Panel value="meta" pt="md">
          <MonacoPanel
            title="/tmp/openai_prompt_meta.json"
            value={JSON.stringify(prompt.data?.metadata ?? {}, null, 2)}
            language="json"
          />
        </Tabs.Panel>
        <Tabs.Panel value="review" pt="md">
          <MonacoPanel title={review.data?.path ?? "/tmp/plex_review.log"} value={review.data?.content} />
        </Tabs.Panel>
      </Tabs>
    </>
  );
}
