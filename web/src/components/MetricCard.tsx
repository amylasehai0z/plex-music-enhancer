import { Card, Group, Text, ThemeIcon } from "@mantine/core";
import type { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
}

export function MetricCard({ label, value, icon: Icon }: MetricCardProps) {
  return (
    <Card withBorder radius="sm" padding="md" className="metric-card">
      <Group justify="space-between" wrap="nowrap">
        <div>
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
            {label}
          </Text>
          <Text size="xl" fw={700}>
            {value}
          </Text>
        </div>
        <ThemeIcon variant="light" color="teal" radius="sm">
          <Icon size={18} />
        </ThemeIcon>
      </Group>
    </Card>
  );
}
