import { Card, Group, Progress, RingProgress, Stack, Text, Tooltip } from "@mantine/core";
import type { ReactNode } from "react";

interface InsightCardProps {
  title: string;
  value?: string | number | null;
  score?: number | null;
  icon?: ReactNode;
  description?: string;
  tone?: "good" | "warn" | "neutral";
}

export function InsightCard({
  title,
  value,
  score,
  icon,
  description,
  tone = "neutral",
}: InsightCardProps) {
  const color = tone === "good" ? "teal" : tone === "warn" ? "yellow" : "blue";
  const normalizedScore = typeof score === "number" ? Math.max(0, Math.min(100, score)) : null;

  return (
    <Card withBorder radius="sm" padding="md" className="insight-card">
      <Group justify="space-between" align="start" wrap="nowrap">
        <Stack gap={4}>
          <Group gap="xs">
            {icon}
            <Tooltip label={description ?? title} disabled={!description}>
              <Text size="sm" fw={700}>
                {title}
              </Text>
            </Tooltip>
          </Group>
          <Text size="xl" fw={800}>
            {value ?? (normalizedScore !== null ? `${normalizedScore}%` : "n/a")}
          </Text>
        </Stack>
        {normalizedScore !== null ? (
          <RingProgress
            size={54}
            thickness={5}
            roundCaps
            sections={[{ value: normalizedScore, color }]}
          />
        ) : null}
      </Group>
      {normalizedScore !== null ? <Progress mt="sm" value={normalizedScore} color={color} /> : null}
    </Card>
  );
}
