import { Card, Group, List, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import { Lightbulb, Route } from "lucide-react";

import { useDeveloperExplain } from "../hooks/useApi";

export function ExplainCard() {
  const explain = useDeveloperExplain();
  const data = explain.data;

  return (
    <Card withBorder radius="sm" padding="md" className="analysis-card">
      <Stack gap="sm">
        <Group gap="sm">
          <ThemeIcon color="yellow" variant="light" radius="sm">
            <Lightbulb size={18} />
          </ThemeIcon>
          <div>
            <Title order={3}>Explain View</Title>
            <Text size="sm" c="dimmed">
              Backend-Erklärung der letzten Review-Entscheidungen.
            </Text>
          </div>
        </Group>
        <List spacing="xs" size="sm" icon={<Route size={14} />}>
          {(data?.summary ?? ["Noch keine Explainability-Daten geladen."]).map((item) => (
            <List.Item key={item}>{item}</List.Item>
          ))}
        </List>
        {data?.recommendations?.length ? (
          <>
            <Text size="sm" fw={700}>
              Empfehlungen
            </Text>
            <List spacing="xs" size="sm">
              {data.recommendations.map((item) => (
                <List.Item key={item}>{item}</List.Item>
              ))}
            </List>
          </>
        ) : null}
      </Stack>
    </Card>
  );
}
