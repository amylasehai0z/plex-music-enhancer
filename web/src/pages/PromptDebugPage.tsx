import { Button, Grid, Group, Tabs, Text, Title } from "@mantine/core";
import { Copy, Download, RefreshCw } from "lucide-react";

import { AnalysisCard } from "../components/AnalysisCard";
import { InsightCard } from "../components/InsightCard";
import { MonacoPanel } from "../components/MonacoPanel";
import { useDebugMeta, useDebugPrompt, useDebugReview } from "../hooks/useApi";

export function PromptDebugPage() {
  const prompt = useDebugPrompt();
  const meta = useDebugMeta();
  const review = useDebugReview();

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
          <Text c="dimmed">Prompt, Meta-Daten und Review-Log aus dem Backend.</Text>
        </div>
        <Group>
          <Button
            leftSection={<RefreshCw size={16} />}
            variant="light"
            onClick={() => {
              void prompt.refetch();
              void meta.refetch();
              void review.refetch();
            }}
          >
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
      <Grid mb="md">
        <Grid.Col span={{ base: 12, md: 3 }}>
          <InsightCard title="Zeichen" value={prompt.data?.stats.characters ?? "n/a"} />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 3 }}>
          <InsightCard title="Tokens" value={prompt.data?.stats.estimatedTokens ?? "n/a"} />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 3 }}>
          <InsightCard title="Budget" value={prompt.data?.stats.budget ?? "n/a"} />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 3 }}>
          <InsightCard title="Prompt-Version" value={prompt.data?.stats.promptVersion ?? "n/a"} />
        </Grid.Col>
      </Grid>
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
            value={JSON.stringify(meta.data?.payload ?? {}, null, 2)}
            language="json"
          />
        </Tabs.Panel>
        <Tabs.Panel value="review" pt="md">
          <MonacoPanel title={review.data?.path ?? "/tmp/plex_review.log"} value={review.data?.content} />
          <Grid mt="md">
            {Object.entries(review.data?.sections ?? {}).map(([title, content]) => (
              <Grid.Col key={title} span={{ base: 12, md: 6 }}>
                <AnalysisCard title={title} data={content.slice(0, 1200)} />
              </Grid.Col>
            ))}
          </Grid>
        </Tabs.Panel>
      </Tabs>
    </>
  );
}
