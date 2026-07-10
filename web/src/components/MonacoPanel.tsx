import { Editor, DiffEditor } from "@monaco-editor/react";
import { Paper, Text } from "@mantine/core";

interface MonacoPanelProps {
  title: string;
  value?: string;
  original?: string;
  modified?: string;
  language?: string;
  height?: number;
}

export function MonacoPanel({
  title,
  value,
  original,
  modified,
  language = "markdown",
  height = 360,
}: MonacoPanelProps) {
  return (
    <Paper withBorder radius="sm" className="monaco-panel">
      <Text fw={700} p="sm">
        {title}
      </Text>
      {original !== undefined || modified !== undefined ? (
        <DiffEditor
          height={height}
          original={original ?? ""}
          modified={modified ?? ""}
          language={language}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            renderSideBySide: true,
            diffWordWrap: "on",
            wordWrap: "on",
            scrollBeyondLastLine: false,
          }}
        />
      ) : (
        <Editor
          height={height}
          value={value ?? ""}
          language={language}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            wordWrap: "on",
            scrollBeyondLastLine: false,
            find: { addExtraSpaceOnTop: false },
          }}
        />
      )}
    </Paper>
  );
}
