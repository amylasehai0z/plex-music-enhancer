import {
  ActionIcon,
  AppShell,
  Badge,
  Group,
  Kbd,
  NavLink,
  Select,
  Text,
  TextInput,
} from "@mantine/core";
import { useDisclosure, useHotkeys } from "@mantine/hooks";
import {
  Album,
  BarChart3,
  Bug,
  ClipboardCheck,
  Command,
  Home,
  Search,
  Settings,
  UserRound,
} from "lucide-react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { CommandPalette } from "../components/CommandPalette";

const navItems = [
  { label: "Dashboard", path: "/", icon: Home },
  { label: "Künstler", path: "/artists", icon: UserRound },
  { label: "Alben", path: "/albums", icon: Album },
  { label: "Reviews", path: "/reviews", icon: ClipboardCheck },
  { label: "Prompt Debug", path: "/prompt-debug", icon: Bug },
  { label: "Einstellungen", path: "/settings", icon: Settings },
];

export function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [opened, { open, close }] = useDisclosure(false);
  useHotkeys([["mod+K", open]]);

  return (
    <AppShell header={{ height: 56 }} navbar={{ width: 260, breakpoint: "sm" }} padding="md">
      <AppShell.Header className="topbar">
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <ActionIcon variant="light" color="teal" radius="sm" onClick={open} aria-label="Command Palette">
              <Command size={18} />
            </ActionIcon>
            <TextInput
              leftSection={<Search size={16} />}
              placeholder="Suchen"
              w={320}
              aria-label="Suche"
            />
            <Kbd>Ctrl K</Kbd>
          </Group>
          <Group gap="sm" wrap="nowrap">
            <Select
              aria-label="Provider"
              data={["openai", "dummy"]}
              defaultValue="openai"
              w={140}
              size="xs"
            />
            <Badge color="teal" variant="light" radius="sm">
              API verbunden
            </Badge>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="md" className="sidebar">
        <Group gap="sm" mb="lg">
          <BarChart3 size={22} />
          <div>
            <Text fw={800}>Plex Music Enhancer</Text>
            <Text size="xs" c="dimmed">
              Review-first Web UI
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
