import { Card, Group, Stack, Text } from "@mantine/core";

import { summarizeObject } from "../utils/format";

interface AnalysisCardProps {
  title: string;
  description?: string;
  data: unknown;
}

export function AnalysisCard({ title, description, data }: AnalysisCardProps) {
  const content = Array.isArray(data)
    ? data.join("\n") || "Keine Einträge"
    : typeof data === "object" && data !== null
      ? summarizeObject(data as Record<string, unknown>)
      : String(data ?? "Keine Daten");

  return (
    <Card withBorder radius="sm" padding="md" className="analysis-card">
      <Stack gap="xs">
        <Group justify="space-between" align="start">
          <Text fw={700}>{title}</Text>
          {description ? (
            <Text size="xs" c="dimmed">
              {description}
            </Text>
          ) : null}
        </Group>
        <Text component="pre" size="sm" className="analysis-pre">
          {content}
        </Text>
      </Stack>
    </Card>
  );
}
