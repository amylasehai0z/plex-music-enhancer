import { Alert, Group, Loader, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";

export function LibraryExplorer({
  description,
  detail,
  list,
  meta,
  title,
  toolbar,
}: {
  description: string;
  detail: ReactNode;
  list: ReactNode;
  meta: ReactNode;
  title: string;
  toolbar: ReactNode;
}) {
  return (
    <Stack gap="md" className="library-explorer">
      <Group justify="space-between" align="flex-end" className="library-explorer-header">
        <div>
          <Title order={1}>{title}</Title>
          <Text c="dimmed">{description}</Text>
        </div>
        <Group align="flex-end" className="library-explorer-toolbar">
          {toolbar}
        </Group>
      </Group>
      <Group justify="space-between" className="selection-bar">
        {meta}
      </Group>
      <div className="library-split-view">
        <section className="surface table-surface library-list-panel">{list}</section>
        <section className="surface library-detail-panel">{detail}</section>
      </div>
    </Stack>
  );
}

export function LibraryLoadingState({ label }: { label: string }) {
  return (
    <section className="surface">
      <Group>
        <Loader size="sm" />
        <Text>{label}</Text>
      </Group>
    </section>
  );
}

export function LibraryErrorState({ error, title }: { error: Error; title: string }) {
  return (
    <Alert color="red" title={title}>
      {error.message}
    </Alert>
  );
}

export function LibraryDetailState({
  children,
  empty,
  error,
  errorTitle,
  loading,
  loadingLabel,
}: {
  children: ReactNode;
  empty: ReactNode;
  error: Error | null;
  errorTitle: string;
  loading: boolean;
  loadingLabel: string;
}) {
  if (loading) {
    return (
      <Group>
        <Loader size="sm" />
        <Text>{loadingLabel}</Text>
      </Group>
    );
  }

  if (error) {
    return (
      <Alert color="red" title={errorTitle}>
        {error.message}
      </Alert>
    );
  }

  return children ?? empty;
}

export function CoverArt({
  label,
  size = "sm",
  src,
}: {
  label: string;
  size?: "sm" | "lg";
  src?: string | null;
}) {
  const className = size === "lg" ? "cover-image cover-image-lg" : "cover-image";
  const placeholderClassName = size === "lg" ? "cover-placeholder cover-placeholder-lg" : "cover-placeholder";

  if (src) {
    return <img src={src} alt={label} className={className} />;
  }
  return <div className={placeholderClassName} aria-label={`${label} nicht vorhanden`} />;
}

export function DetailMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text fw={800}>{value}</Text>
    </div>
  );
}
