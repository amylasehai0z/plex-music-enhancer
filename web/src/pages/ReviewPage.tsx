import {
  Button,
  Grid,
  Group,
  NativeSelect,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Play } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

import { AnalysisCard } from "../components/AnalysisCard";
import { MonacoPanel } from "../components/MonacoPanel";
import { StatusPill } from "../components/StatusPill";
import { useReviewMutation } from "../hooks/useApi";
import type { ReviewTarget } from "../types/api";

export function ReviewPage() {
  const [target, setTarget] = useState<ReviewTarget>("album");
  const [artist, setArtist] = useState("Jennifer Rush");
  const [album, setAlbum] = useState("Credo");
  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState("gpt-5.5");
  const review = useReviewMutation();
  const document = review.data?.document;

  const promptDiagnostics = useMemo(
    () => ({
      characters: document?.prompt.characters,
      estimatedTokens: document?.prompt.estimatedTokens,
      efficiency: document?.prompt.efficiency,
      budget: document?.prompt.budget,
    }),
    [document],
  );

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
          <Grid>
            <Grid.Col span={{ base: 12, lg: 6 }}>
              <Textarea
                label="Aktuelle Beschreibung"
                value={document.currentSummary}
                minRows={8}
                readOnly
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, lg: 6 }}>
              <Textarea
                label="Neue Beschreibung"
                value={document.generatedSummary}
                minRows={8}
                readOnly
              />
            </Grid.Col>
          </Grid>
          <MonacoPanel
            title="Unified Diff"
            original={document.currentSummary}
            modified={document.generatedSummary}
            language="markdown"
            height={420}
          />
          <Grid>
            <Grid.Col span={{ base: 12, md: 6, xl: 3 }}>
              <AnalysisCard title="QA" data={document.qa} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6, xl: 3 }}>
              <AnalysisCard title="Editorial" data={document.editorial} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6, xl: 3 }}>
              <AnalysisCard title="Verification" data={document.verification} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6, xl: 3 }}>
              <AnalysisCard title="Prompt Budget" data={promptDiagnostics} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6, xl: 3 }}>
              <AnalysisCard title="Prompt Decisions" data={document.prompt.decisions} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6, xl: 3 }}>
              <AnalysisCard title="Prompt Quality" data={document.prompt.quality} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6, xl: 3 }}>
              <AnalysisCard title="Prompt Efficiency" data={document.prompt.efficiency} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6, xl: 3 }}>
              <AnalysisCard title="Prompt Utilization" data={document.prompt.utilization} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6, xl: 3 }}>
              <AnalysisCard title="Evidence Ranking" data={document.prompt.evidenceRanking} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6, xl: 3 }}>
              <AnalysisCard title="Evidence Coverage" data={document.prompt.evidenceCoverage} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6, xl: 3 }}>
              <AnalysisCard title="Editorial Coverage" data={document.prompt.editorialCoverage} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6, xl: 3 }}>
              <AnalysisCard title="Missed Opportunities" data={document.prompt.missedOpportunities} />
            </Grid.Col>
          </Grid>
        </>
      ) : null}
    </Stack>
  );
}
