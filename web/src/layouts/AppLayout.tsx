import {
  ActionIcon,
  AppShell,
  Badge,
  Group,
  Kbd,
  NavLink,
  Select,
  Switch,
  Text,
  TextInput,
  Tooltip,
  useMantineColorScheme,
} from "@mantine/core";
import { useDisclosure, useHotkeys } from "@mantine/hooks";
import {
  Album,
  Bell,
  Bug,
  ClipboardCheck,
  Command,
  Home,
  ListChecks,
  ListTree,
  Moon,
  RadioTower,
  Search,
  Settings,
  TerminalSquare,
  UserRound,
} from "lucide-react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { CommandPalette } from "../components/CommandPalette";
import { useProviders } from "../hooks/useApi";
import { useDeveloperMode } from "../stores/developerMode";

const navItems = [
  { label: "Dashboard", path: "/", icon: Home },
  { label: "Künstler", path: "/artists", icon: UserRound },
  { label: "Alben", path: "/albums", icon: Album },
  { label: "Batch", path: "/batch", icon: ListChecks },
  { label: "Reviews", path: "/reviews", icon: ClipboardCheck },
  { label: "Prompt Debug", path: "/prompt-debug", icon: Bug },
  { label: "Live Log", path: "/live-log", icon: RadioTower },
  { label: "Developer", path: "/developer", icon: TerminalSquare },
  { label: "REST Explorer", path: "/rest-explorer", icon: ListTree },
  { label: "Einstellungen", path: "/settings", icon: Settings },
];

export function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [opened, { open, close }] = useDisclosure(false);
  const { enabled, toggle } = useDeveloperMode();
  const { setColorScheme } = useMantineColorScheme();
  const providers = useProviders();
  const aiProvider = providers.data?.find((item) => item.details.type === "ai");
  useHotkeys([["mod+K", open]]);

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 260, breakpoint: "sm" }}
      padding="md"
    >
      <AppShell.Header className="topbar">
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <ActionIcon variant="light" color="teal" radius="sm" onClick={open} aria-label="Command Palette">
              <Command size={18} />
            </ActionIcon>
            <TextInput leftSection={<Search size={16} />} placeholder="Suchen" w={320} aria-label="Suche" />
            <Kbd>Ctrl K</Kbd>
          </Group>
          <Group gap="sm" wrap="nowrap">
            <Select
              aria-label="Provider"
              data={providers.data?.map((item) => item.name) ?? ["openai", "dummy"]}
              value={aiProvider?.name ?? "openai"}
              w={140}
              size="xs"
              readOnly
            />
            <Badge color="blue" variant="light" radius="sm">
              {aiProvider?.model ?? "Modell offen"}
            </Badge>
            <Tooltip label="Developer Mode">
              <Switch
                size="sm"
                checked={enabled}
                onChange={toggle}
                onLabel="DEV"
                offLabel="DEV"
              />
            </Tooltip>
            <ActionIcon
              variant="subtle"
              color="gray"
              radius="sm"
              aria-label="Theme"
              onClick={() => setColorScheme("dark")}
            >
              <Moon size={18} />
            </ActionIcon>
            <ActionIcon variant="subtle" color="gray" radius="sm" aria-label="Benachrichtigungen">
              <Bell size={18} />
            </ActionIcon>
            <Badge color="teal" variant="light" radius="sm">
              API verbunden
            </Badge>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="md" className="sidebar">
        <Group gap="sm" mb="lg" wrap="nowrap" className="brand-lockup">
          <img src="/logo/plex-music-enhancer-logo.svg" alt="" className="brand-logo" />
          <div>
            <Text fw={800}>Plex Music Enhancer</Text>
            <Text size="xs" c="dimmed">
              Review-first Desktop UI
            </Text>
          </div>
        </Group>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            active={location.pathname === item.path}
            label={item.label}
            leftSection={<item.icon size={18} />}
            onClick={() => navigate(item.path)}
            variant="filled"
          />
        ))}
      </AppShell.Navbar>
      <AppShell.Main className="workspace">
        <Outlet />
      </AppShell.Main>
      <CommandPalette opened={opened} onClose={close} />
    </AppShell>
  );
}
