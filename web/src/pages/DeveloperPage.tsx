import { Grid, Group, List, Stack, Text, Title } from "@mantine/core";
import { Bug, Gauge, GitBranch, Lightbulb, ShieldCheck } from "lucide-react";
import { FaGithub } from "react-icons/fa";

import { AnalysisCard } from "../components/AnalysisCard";
import { ExplainCard } from "../components/ExplainCard";
import { InsightCard } from "../components/InsightCard";
import { useDeveloperDoctor } from "../hooks/useApi";

export function DeveloperPage() {
  const doctor = useDeveloperDoctor();
  const report = doctor.data;

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <div>
          <Title order={1}>Developer</Title>
          <Text c="dimmed">Prompt-, Evidence- und Review-Diagnostik aus dem Backend.</Text>
        </div>
        <Group gap="xs">
          <FaGithub aria-hidden />
          <Text size="sm" c="dimmed">
            Issue-ready JSON über REST
          </Text>
        </Group>
      </Group>
      <Grid>
        <Grid.Col span={{ base: 12, md: 3 }}>
          <InsightCard
            title="Promptgröße"
            value={report?.prompt.stats.characters ?? "n/a"}
            score={_budgetScore(report?.prompt.stats.characters, report?.prompt.stats.budget)}
            icon={<Gauge size={16} />}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 3 }}>
          <InsightCard
            title="Token"
            value={report?.prompt.stats.estimatedTokens ?? "n/a"}
            icon={<GitBranch size={16} />}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 3 }}>
          <InsightCard
            title="Review Log"
            value={report?.review.exists ? "OK" : "Fehlt"}
            score={report?.review.exists ? 100 : 0}
            icon={<Bug size={16} />}
            tone={report?.review.exists ? "good" : "warn"}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 3 }}>
          <InsightCard
            title="Verification"
            value={report?.checks.verification ?? "n/a"}
            score={report?.checks.verification === "PASS" ? 100 : 35}
            icon={<ShieldCheck size={16} />}
          />
        </Grid.Col>
      </Grid>
      <Grid>
        <Grid.Col span={{ base: 12, xl: 7 }}>
          <ExplainCard />
        </Grid.Col>
        <Grid.Col span={{ base: 12, xl: 5 }}>
          <AnalysisCard title="Doctor Checks" data={report?.checks ?? {}} />
        </Grid.Col>
        <Grid.Col span={{ base: 12, xl: 6 }}>
          <AnalysisCard title="Prompt Decisions" data={report?.explanation.promptDecisions ?? {}} />
        </Grid.Col>
        <Grid.Col span={{ base: 12, xl: 6 }}>
          <AnalysisCard title="Used Sources" data={report?.explanation.usedSources ?? {}} />
        </Grid.Col>
      </Grid>
      <section className="surface">
        <Group gap="sm" mb="sm">
          <Lightbulb size={18} />
          <Title order={2}>Developer Mode Workflow</Title>
        </Group>
        <List spacing="xs" size="sm">
          <List.Item>Review erzeugen oder Prompt Debug aktualisieren.</List.Item>
          <List.Item>Developer Mode in der Topbar aktivieren.</List.Item>
          <List.Item>Prompt Decisions, Coverage und Missed Opportunities prüfen.</List.Item>
          <List.Item>Bei Bedarf Debug-JSON für Issues exportieren.</List.Item>
        </List>
      </section>
    </Stack>
  );
}

function _budgetScore(characters?: number | null, budget?: number | null): number | null {
  if (!characters || !budget) {
    return null;
  }
  return Math.round((characters / budget) * 100);
}
