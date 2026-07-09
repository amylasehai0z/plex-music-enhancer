import { Button, Grid, JsonInput, Stack, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../api/client";

export function SettingsPage() {
  const config = useQuery({ queryKey: ["configuration"], queryFn: () => api.config.get() });
  const [value, setValue] = useState("{}");
  const update = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.config.update(payload),
    onSuccess: () => notifications.show({ color: "teal", message: "Konfiguration geprüft." }),
    onError: (error) => notifications.show({ color: "red", message: error.message }),
  });

  useEffect(() => {
    if (config.data) {
      setValue(JSON.stringify(config.data.configuration, null, 2));
    }
  }, [config.data]);

  return (
    <Stack gap="md">
      <div>
        <Title order={1}>Einstellungen</Title>
        <Text c="dimmed">Sanitisierte Konfiguration aus der REST-API.</Text>
      </div>
      <Grid>
        <Grid.Col span={{ base: 12, lg: 8 }}>
          <JsonInput
            value={value}
            onChange={setValue}
            minRows={20}
            autosize
            formatOnBlur
            validationError="Ungültiges JSON"
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 4 }}>
          <section className="surface">
            <Title order={2}>Hinweis</Title>
            <Text size="sm" c="dimmed">
              Persistente Konfigurationsänderungen werden vom Backend vorbereitet. Diese Ansicht
              spricht ausschließlich mit der REST-API.
            </Text>
            <Button
              mt="md"
              onClick={() => update.mutate(JSON.parse(value) as Record<string, unknown>)}
              loading={update.isPending}
            >
              Über REST-API prüfen
            </Button>
          </section>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
