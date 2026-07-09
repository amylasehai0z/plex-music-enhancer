import { Badge } from "@mantine/core";

interface StatusPillProps {
  value: string | boolean | null | undefined;
}

export function StatusPill({ value }: StatusPillProps) {
  const label = typeof value === "boolean" ? (value ? "OK" : "Offen") : (value ?? "Unbekannt");
  const color = value === true || value === "PASS" || value === "ok" ? "teal" : "orange";
  return (
    <Badge color={color} variant="light" radius="sm">
      {label}
    </Badge>
  );
}
