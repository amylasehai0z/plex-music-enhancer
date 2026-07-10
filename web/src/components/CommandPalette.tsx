import { Modal, Stack, TextInput, UnstyledButton } from "@mantine/core";
import { Search } from "lucide-react";
import { useNavigate } from "react-router-dom";

const commands = [
  { label: "Dashboard öffnen", path: "/" },
  { label: "Künstler anzeigen", path: "/artists" },
  { label: "Alben anzeigen", path: "/albums" },
  { label: "Review starten", path: "/reviews" },
  { label: "Prompt Debug öffnen", path: "/prompt-debug" },
  { label: "Live Log öffnen", path: "/live-log" },
  { label: "Developer öffnen", path: "/developer" },
  { label: "REST Explorer öffnen", path: "/rest-explorer" },
  { label: "Einstellungen öffnen", path: "/settings" },
];

interface CommandPaletteProps {
  opened: boolean;
  onClose: () => void;
}

export function CommandPalette({ opened, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();

  return (
    <Modal opened={opened} onClose={onClose} title="Command Palette" size="lg">
      <Stack gap="xs">
        <TextInput leftSection={<Search size={16} />} placeholder="Befehl suchen" autoFocus />
        {commands.map((command) => (
          <UnstyledButton
            key={command.path}
            className="command-item"
            onClick={() => {
              navigate(command.path);
              onClose();
            }}
          >
            {command.label}
          </UnstyledButton>
        ))}
      </Stack>
    </Modal>
  );
}
