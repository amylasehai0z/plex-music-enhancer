import { Alert, Badge, Button, Card, Grid, Group, Stack, Text, Title } from "@mantine/core";
import { useQueryClient } from "@tanstack/react-query";
import { Play, Star } from "lucide-react";

import { StatusPill } from "../components/StatusPill";
import { useAlbumReviewGenerationMutation, useAlbumReviews } from "../hooks/useApi";

export function AlbumReviewsPage() {
  const queryClient = useQueryClient();
  const reviews = useAlbumReviews();
  const generate = useAlbumReviewGenerationMutation();

  function generateReview(albumId: string) {
    generate.mutate(albumId, {
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["albumReviews"] });
        await queryClient.invalidateQueries({ queryKey: ["statistics"] });
      },
    });
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <div>
          <Title order={1}>Reviews</Title>
          <Text c="dimmed">Strukturierte AI-Albumkritiken aus synchronisierten Plex-Alben.</Text>
        </div>
        <Badge color="teal" variant="light">
          {reviews.data?.generatedReviews ?? 0} generiert
        </Badge>
      </Group>

      {reviews.isError ? (
        <Alert color="red">{reviews.error.message}</Alert>
      ) : null}

      <Grid>
        {(reviews.data?.albums ?? []).map((album) => (
          <Grid.Col key={album.albumId} span={{ base: 12, md: 6, xl: 4 }}>
            <Card withBorder radius="sm" className="surface">
              <Stack gap="sm">
                <Group justify="space-between" align="start">
                  <Group align="start" wrap="nowrap">
                    <div className="cover-placeholder" />
                    <div>
                      <Title order={3}>{album.album}</Title>
                      <Text c="dimmed" size="sm">
                        {album.artist}
                        {album.year ? ` · ${album.year}` : ""}
                      </Text>
                    </div>
                  </Group>
                  <ReviewStatus status={album.reviewStatus} />
                </Group>

                <Group gap="xs">
                  <Badge variant="light">{album.trackCount} Tracks</Badge>
                  {album.rating !== null && album.rating !== undefined ? (
                    <Badge color="yellow" leftSection={<Star size={12} />}>
                      {album.rating}/100
                    </Badge>
                  ) : null}
                </Group>

                <Text size="sm" lineClamp={4}>
                  {album.summary ?? "Noch keine strukturierte Albumkritik vorhanden."}
                </Text>

                {album.review ? (
                  <Stack gap={4}>
                    <Text size="sm" fw={700}>
                      Fazit
                    </Text>
                    <Text size="sm">{album.review.content.finalVerdict}</Text>
                    <Text size="xs" c="dimmed">
                      {album.review.provider} · {album.review.model}
                    </Text>
                  </Stack>
                ) : null}

                {album.error ? <Alert color="red">{album.error}</Alert> : null}

                <Button
                  leftSection={<Play size={16} />}
                  onClick={() => generateReview(album.albumId)}
                  loading={album.running || (generate.isPending && generate.variables === album.albumId)}
                  disabled={album.running}
                >
                  Review generieren
                </Button>
              </Stack>
            </Card>
          </Grid.Col>
        ))}
      </Grid>

      {!reviews.isLoading && !reviews.data?.albums.length ? (
        <section className="surface">
          <Text c="dimmed">Noch keine synchronisierten Alben vorhanden. Starte zuerst die Plex Synchronisation.</Text>
        </section>
      ) : null}
    </Stack>
  );
}

function ReviewStatus({ status }: { status: string }) {
  if (status === "present") {
    return <StatusPill value />;
  }
  if (status === "running") {
    return <Badge color="blue">läuft</Badge>;
  }
  if (status === "error") {
    return <Badge color="red">Fehler</Badge>;
  }
  return <Badge color="gray">nicht vorhanden</Badge>;
}
