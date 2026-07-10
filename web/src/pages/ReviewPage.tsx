import {
  Accordion,
  ActionIcon,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  NativeSelect,
  ScrollArea,
  Stack,
  Text,
  TextInput,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useHotkeys, useLocalStorage } from "@mantine/hooks";
import { Check, Eye, FileDiff, Play, Sparkles } from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { AnalysisCard } from "../components/AnalysisCard";
import { ExplainCard } from "../components/ExplainCard";
import { MonacoPanel } from "../components/MonacoPanel";
import { ReviewAnalysisSidebar } from "../components/ReviewAnalysisSidebar";
import { StatusPill } from "../components/StatusPill";
import { useApplyMutation, useReviewMutation } from "../hooks/useApi";
import { useDeveloperMode } from "../stores/developerMode";
import type { ReviewTarget } from "../types/api";

export function ReviewPage() {
  const [searchParams] = useSearchParams();
  const [target, setTarget] = useState<ReviewTarget>((searchParams.get("target") as ReviewTarget) || "album");
  const [artist, setArtist] = useState(searchParams.get("artist") || "Jennifer Rush");
  const [album, setAlbum] = useState(searchParams.get("album") || "Credo");
  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState("gpt-5.5");
  const diffRef = useRef<HTMLDivElement>(null);
  const [split, setSplit] = useLocalStorage({ key: "pme:review-split", defaultValue: 50 });
  const review = useReviewMutation();
  const apply = useApplyMutation();
  const autoRunKey = useRef<string | null>(null);
  const document = review.data?.document;
  const { enabled: developerMode, toggle: toggleDeveloperMode } = useDeveloperMode();

  const promptDiagnostics = useMemo(
    () => ({
      characters: document?.prompt.characters,
      estimatedTokens: document?.prompt.estimatedTokens,
      efficiency: document?.prompt.efficiency,
      budget: document?.prompt.budget,
    }),
    [document],
  );
  const developerPanels = useMemo(
    () =>
      document
        ? [
            ["Prompt Decisions", document.prompt.decisions],
            ["Prompt Quality", document.prompt.quality],
            ["Prompt Efficiency", document.prompt.efficiency],
            ["Prompt Utilization", document.prompt.utilization],
            ["Evidence Ranking", document.prompt.evidenceRanking],
            ["Evidence Coverage", document.prompt.evidenceCoverage],
            ["Editorial Coverage", document.prompt.editorialCoverage],
            ["Editorial Balance", document.prompt.editorialBalance],
            ["Missed Opportunities", document.prompt.missedOpportunities],
            ["Debug Meta", document.debug],
            ["Provider Meta", { provider: document.provider, model: document.model }],
            ["Timing", { generationTimeSeconds: document.debug.generationTimeSeconds }],
            ["Token Usage", document.debug.tokenUsage],
          ] as const
        : [],
    [document],
  );

  useHotkeys([
    ["r", () => review.reset()],
    ["p", () => notifications.show({ message: "Preview läuft über denselben Backend-Flow." })],
    ["a", () => notifications.show({ message: "Apply bleibt review-first im Backend abgesichert." })],
    ["d", () => diffRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })],
    ["e", () => document && notifications.show({ message: "Explain View ist sichtbar." })],
    ["mod+shift+D", toggleDeveloperMode],
  ]);

  useEffect(() => {
    const nextTarget = (searchParams.get("target") as ReviewTarget) || "album";
    const nextArtist = searchParams.get("artist") || "Jennifer Rush";
    const nextAlbum = searchParams.get("album") || "Credo";
    setTarget(nextTarget);
    setArtist(nextArtist);
    setAlbum(nextAlbum);

    const shouldRun = searchParams.get("run") === "1";
    const key = `${nextTarget}:${nextArtist}:${nextAlbum}`;
    if (shouldRun && autoRunKey.current !== key) {
      autoRunKey.current = key;
      review.mutate(
        {
          target: nextTarget,
          artist: nextArtist,
          album: nextTarget === "album" ? nextAlbum : undefined,
          provider,
          model,
        },
        {
          onError: (error) => notifications.show({ color: "red", message: error.message }),
        },
      );
    }
  }, [model, provider, review, searchParams]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    review.mutate(
      {
        target,
        artist,
        album: target === "album" ? album : undefined,
        provider,
        model,
      },
      {
        onError: (error) => notifications.show({ color: "red", message: error.message }),
      },
    );
  }

  function startResize() {
    function onMove(event: MouseEvent) {
      const viewportWidth = Math.max(globalThis.document.documentElement.clientWidth, 1);
      const next = Math.round((event.clientX / viewportWidth) * 100);
      setSplit(Math.max(34, Math.min(66, next)));
    }

    function onUp() {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    }

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }

  function applyCurrentReview() {
    apply.mutate(
      {
        target,
        artist,
        album: target === "album" ? album : undefined,
        provider,
        model,
      },
      {
        onSuccess: () => notifications.show({ color: "teal", message: "Review erfolgreich übernommen." }),
        onError: (error) => notifications.show({ color: "red", message: error.message }),
      },
    );
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <div>
          <Title order={1}>Reviews</Title>
          <Text c="dimmed">Generierte Beschreibungen prüfen, vergleichen und vorbereiten.</Text>
        </div>
        {document ? <StatusPill value={document.qa.status} /> : null}
      </Group>
      <form onSubmit={submit} className="surface">
        <Grid align="end">
          <Grid.Col span={{ base: 12, md: 2 }}>
            <NativeSelect
              label="Ziel"
              value={target}
              onChange={(event) => setTarget(event.currentTarget.value as ReviewTarget)}
              data={[
                { value: "album", label: "Album" },
                { value: "artist", label: "Künstler" },
              ]}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <TextInput label="Künstler" value={artist} onChange={(event) => setArtist(event.currentTarget.value)} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 3 }}>
            <TextInput
              label="Album"
              value={album}
              disabled={target === "artist"}
              onChange={(event) => setAlbum(event.currentTarget.value)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 2 }}>
            <TextInput label="Provider" value={provider} onChange={(event) => setProvider(event.currentTarget.value)} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 2 }}>
            <TextInput label="Modell" value={model} onChange={(event) => setModel(event.currentTarget.value)} />
          </Grid.Col>
          <Grid.Col span={12}>
            <Button type="submit" leftSection={<Play size={16} />} loading={review.isPending}>
              Review erzeugen
            </Button>
          </Grid.Col>
        </Grid>
      </form>
      {document ? (
        <>
          <Card withBorder radius="sm" className="review-hero">
            <Group justify="space-between" align="start">
              <Group align="start">
                <div className="review-artwork" />
                <div>
                  <Group gap="xs">
                    <Badge color={document.target === "album" ? "blue" : "teal"}>
                      {document.target}
                    </Badge>
                    <Badge color="gray">{document.mode}</Badge>
                  </Group>
                  <Title order={2}>{document.album ?? document.artist}</Title>
                  <Text c="dimmed">
                    {document.artist}
                    {document.album ? ` · ${document.album}` : ""}
                  </Text>
                  <Text size="sm" c="dimmed">
                    {document.provider} · {document.model} · {document.debug.generationTimeSeconds}s
                  </Text>
                </div>
              </Group>
              <Group>
                <Tooltip label="Preview">
                  <ActionIcon variant="light" color="blue" radius="sm" aria-label="Preview">
                    <Eye size={18} />
                  </ActionIcon>
                </Tooltip>
                <Tooltip label="Apply">
                  <ActionIcon
                    variant="light"
                    color="teal"
                    radius="sm"
                    aria-label="Apply"
                    loading={apply.isPending}
                    onClick={applyCurrentReview}
                  >
                    <Check size={18} />
                  </ActionIcon>
                </Tooltip>
              </Group>
            </Group>
          </Card>
          <Grid align="stretch">
            <Grid.Col span={{ base: 12, xl: 8 }}>
              <Stack gap="md">
                <div
                  className="review-split"
                  style={{ gridTemplateColumns: `${split}fr 10px ${100 - split}fr` }}
                >
                  <div>
                    <DescriptionPane title="Aktuelle Plex-Beschreibung" text={document.currentSummary} />
                  </div>
                  <button
                    type="button"
                    className="splitter-handle"
                    aria-label="Panelgrößen ändern"
                    onMouseDown={startResize}
                  />
                  <div>
                    <DescriptionPane
                      title="Neu generierte Beschreibung"
                      text={document.generatedSummary}
                    />
                  </div>
                </div>
                <div ref={diffRef}>
                  <Accordion defaultValue="diff" variant="contained">
                    <Accordion.Item value="diff">
                      <Accordion.Control icon={<FileDiff size={18} />}>Diff</Accordion.Control>
                      <Accordion.Panel>
                        <MonacoPanel
                          title="Monaco Diff"
                          original={document.currentSummary}
                          modified={document.generatedSummary}
                          language="markdown"
                          height={460}
                        />
                      </Accordion.Panel>
                    </Accordion.Item>
                  </Accordion>
                </div>
                <ExplainCard />
                {developerMode ? (
                  <Grid>
                    {developerPanels.map(([title, data]) => (
                      <Grid.Col key={title} span={{ base: 12, md: 6 }}>
                        <AnalysisCard title={title} data={data} />
                      </Grid.Col>
                    ))}
                  </Grid>
                ) : (
                  <Grid>
                    <Grid.Col span={{ base: 12, md: 4 }}>
                      <AnalysisCard title="QA" data={document.qa} />
                    </Grid.Col>
                    <Grid.Col span={{ base: 12, md: 4 }}>
                      <AnalysisCard title="Editorial" data={document.editorial} />
                    </Grid.Col>
                    <Grid.Col span={{ base: 12, md: 4 }}>
                      <AnalysisCard title="Verification" data={document.verification} />
                    </Grid.Col>
                  </Grid>
                )}
              </Stack>
            </Grid.Col>
            <Grid.Col span={{ base: 12, xl: 4 }}>
              <ReviewAnalysisSidebar document={document} />
            </Grid.Col>
          </Grid>
        </>
      ) : null}
    </Stack>
  );
}

function DescriptionPane({ title, text }: { title: string; text: string }) {
  return (
    <Card withBorder radius="sm" className="description-pane">
      <Group justify="space-between" mb="xs">
        <Text fw={700}>{title}</Text>
        <Sparkles size={16} />
      </Group>
      <ScrollArea h={280} type="hover">
        <Text className="description-text">{text || "Keine Beschreibung vorhanden."}</Text>
      </ScrollArea>
    </Card>
  );
}
