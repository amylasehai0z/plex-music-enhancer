import { Accordion, Badge, Group, Progress, RingProgress, Stack, Text, Timeline, Title } from "@mantine/core";
import { BarChart3, CheckCircle2, Gauge, GitBranch, Route, ShieldCheck } from "lucide-react";

import { useDeveloperMode } from "../stores/developerMode";
import type { ReviewDocument } from "../types/api";
import { InsightCard } from "./InsightCard";

interface ReviewAnalysisSidebarProps {
  document: ReviewDocument;
}

export function ReviewAnalysisSidebar({ document }: ReviewAnalysisSidebarProps) {
  const { enabled } = useDeveloperMode();
  const promptBudget = document.prompt.budget
    ? Math.round((document.prompt.characters / document.prompt.budget) * 100)
    : null;

  return (
    <aside className="review-sidebar">
      <Stack gap="md">
        <div>
          <Title order={3}>Analyse</Title>
          <Text size="sm" c="dimmed">
            Kontextabhängige Review-Diagnostik.
          </Text>
        </div>
        <InsightCard
          title="QA"
          value={document.qa.status}
          score={document.qa.overallScore ?? (document.qa.publishable ? 100 : 35)}
          icon={<CheckCircle2 size={16} />}
          tone={document.qa.publishable ? "good" : "warn"}
        />
        <InsightCard
          title="Editorial"
          value={document.editorial.level ?? "n/a"}
          score={document.editorial.score}
          icon={<BarChart3 size={16} />}
          tone="good"
        />
        <InsightCard
          title="Verification"
          value={`${document.verification.coverageScore}%`}
          score={document.verification.coverageScore}
          icon={<ShieldCheck size={16} />}
          tone={document.verification.conflictingFacts ? "warn" : "good"}
        />
        <Accordion multiple defaultValue={["quality", "timeline"]} variant="separated">
          <Accordion.Item value="quality">
            <Accordion.Control icon={<BarChart3 size={16} />}>Qualität</Accordion.Control>
            <Accordion.Panel>
              <QualityRings document={document} />
            </Accordion.Panel>
          </Accordion.Item>
          <Accordion.Item value="coverage">
            <Accordion.Control icon={<ShieldCheck size={16} />}>Coverage</Accordion.Control>
            <Accordion.Panel>
              <CoverageList data={document.prompt.editorialCoverage} />
            </Accordion.Panel>
          </Accordion.Item>
          {enabled ? (
            <>
              <Accordion.Item value="prompt-budget">
                <Accordion.Control icon={<GitBranch size={16} />}>Prompt Budget</Accordion.Control>
                <Accordion.Panel>
                  <PromptBudget document={document} promptBudget={promptBudget} />
                </Accordion.Panel>
              </Accordion.Item>
              <Accordion.Item value="evidence">
                <Accordion.Control icon={<Gauge size={16} />}>Evidence Ranking</Accordion.Control>
                <Accordion.Panel>
                  <EvidenceBars ranking={document.prompt.evidenceRanking} />
                </Accordion.Panel>
              </Accordion.Item>
              <Accordion.Item value="decisions">
                <Accordion.Control icon={<Route size={16} />}>Prompt Decisions</Accordion.Control>
                <Accordion.Panel>
                  <DecisionTimeline decisions={document.prompt.decisions} />
                </Accordion.Panel>
              </Accordion.Item>
            </>
          ) : null}
          <Accordion.Item value="timeline">
            <Accordion.Control icon={<Route size={16} />}>Review Timeline</Accordion.Control>
            <Accordion.Panel>
              <ReviewTimeline document={document} />
            </Accordion.Panel>
          </Accordion.Item>
        </Accordion>
      </Stack>
    </aside>
  );
}

function QualityRings({ document }: { document: ReviewDocument }) {
  const rings = [
    { label: "QA", value: document.qa.overallScore ?? (document.qa.publishable ? 100 : 35), color: "teal" },
    { label: "Editorial", value: document.editorial.score ?? 0, color: "blue" },
    { label: "Verification", value: document.verification.coverageScore, color: "yellow" },
  ];

  return (
    <Group justify="space-between" wrap="nowrap">
      {rings.map((ring) => (
        <Stack key={ring.label} gap={4} align="center">
          <RingProgress size={72} thickness={7} sections={[{ value: clampScore(ring.value), color: ring.color }]} />
          <Text size="xs" fw={700}>
            {ring.label}
          </Text>
        </Stack>
      ))}
    </Group>
  );
}

function PromptBudget({
  document,
  promptBudget,
}: {
  document: ReviewDocument;
  promptBudget: number | null;
}) {
  const reserve = promptBudget === null ? null : Math.max(0, 100 - promptBudget);
  return (
    <Stack gap="xs">
      <MetricRow label="Promptgröße" value={`${document.prompt.characters.toLocaleString("de-DE")} Zeichen`} />
      <MetricRow label="Tokens" value={document.prompt.estimatedTokens.toLocaleString("de-DE")} />
      <MetricRow label="Budget" value={document.prompt.budget?.toLocaleString("de-DE") ?? "n/a"} />
      <MetricRow label="Auslastung" value={promptBudget !== null ? `${promptBudget}%` : "n/a"} />
      <Progress value={promptBudget ?? 0} color="teal" />
      <MetricRow label="Budget Reserve" value={reserve !== null ? `${reserve}%` : "n/a"} />
      <MetricRow label="Genutzte Evidenz" value={String(document.prompt.utilization.evidenceUsed ?? "n/a")} />
      <MetricRow label="Ungenutzte Evidenz" value={String(document.prompt.utilization.unusedEvidence ?? "n/a")} />
    </Stack>
  );
}

function EvidenceBars({ ranking }: { ranking: Record<string, number> }) {
  const entries = Object.entries(ranking).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    return <Text size="sm" c="dimmed">Keine Evidence-Ranking-Daten vorhanden.</Text>;
  }

  return (
    <Stack gap="xs">
      {entries.map(([source, score]) => (
        <Stack key={source} gap={4}>
          <Group justify="space-between">
            <Text size="sm">{source}</Text>
            <Text size="xs" c="dimmed">{Math.round(score)}%</Text>
          </Group>
          <Progress value={clampScore(score)} color="teal" />
        </Stack>
      ))}
    </Stack>
  );
}

function CoverageList({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data);
  if (!entries.length) {
    return <Text size="sm" c="dimmed">Keine Coverage-Daten vorhanden.</Text>;
  }

  return (
    <Stack gap="xs">
      {entries.map(([label, value]) => {
        const active = Boolean(value);
        return (
          <Group key={label} justify="space-between">
            <Text size="sm">{humanize(label)}</Text>
            <Badge color={active ? "teal" : "yellow"} variant="light">
              {active ? "OK" : "Offen"}
            </Badge>
          </Group>
        );
      })}
    </Stack>
  );
}

function DecisionTimeline({ decisions }: { decisions: Record<string, string[]> }) {
  const entries = Object.entries(decisions);
  if (!entries.length) {
    return <Text size="sm" c="dimmed">Keine Prompt Decisions vorhanden.</Text>;
  }

  return (
    <Timeline active={entries.length} bulletSize={18} lineWidth={2}>
      {entries.map(([title, items]) => (
        <Timeline.Item key={title} title={humanize(title)}>
          <Text size="xs" c="dimmed">
            {items.slice(0, 3).join(" · ") || "Aus Backend-Diagnostik übernommen"}
          </Text>
        </Timeline.Item>
      ))}
    </Timeline>
  );
}

function ReviewTimeline({ document }: { document: ReviewDocument }) {
  const steps = [
    ["Prompt erstellt", true],
    ["Prompt Budget", document.prompt.trimmed || document.prompt.characters > 0],
    ["Provider", Boolean(document.provider)],
    ["Antwort", Boolean(document.generatedSummary)],
    ["QA", Boolean(document.qa.status)],
    ["Editorial", document.editorial.score !== null || document.editorial.level !== null],
    ["Verification", document.verification.coverageScore >= 0],
    ["Review", true],
    ["Fertig", document.qa.publishable],
  ] as const;

  return (
    <Timeline active={steps.filter(([, done]) => done).length - 1} bulletSize={18} lineWidth={2}>
      {steps.map(([label, done]) => (
        <Timeline.Item key={label} title={label}>
          <Text size="xs" c={done ? "teal" : "dimmed"}>
            {done ? "abgeschlossen" : "offen"}
          </Text>
        </Timeline.Item>
      ))}
    </Timeline>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <Group justify="space-between" gap="sm">
      <Text size="sm" c="dimmed">{label}</Text>
      <Text size="sm" fw={700}>{value}</Text>
    </Group>
  );
}

function clampScore(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function humanize(value: string) {
  return value.replaceAll("_", " ").replaceAll("-", " ");
}
