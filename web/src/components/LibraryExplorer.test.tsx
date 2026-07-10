import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LibraryExplorer } from "./LibraryExplorer";

describe("LibraryExplorer", () => {
  it("renders a shared library explorer shell", () => {
    render(
      <MantineProvider>
        <LibraryExplorer
          title="Bibliothek"
          description="Gemeinsame Explorer-Struktur"
          toolbar={<button type="button">Filter</button>}
          meta={<span>2 sichtbar</span>}
          list={<div>Liste links</div>}
          detail={<div>Details rechts</div>}
        />
      </MantineProvider>,
    );

    expect(screen.getByRole("heading", { name: "Bibliothek" })).toBeInTheDocument();
    expect(screen.getByText("Gemeinsame Explorer-Struktur")).toBeInTheDocument();
    expect(screen.getByText("Liste links")).toBeInTheDocument();
    expect(screen.getByText("Details rechts")).toBeInTheDocument();
    expect(screen.getByText("2 sichtbar")).toBeInTheDocument();
  });
});
