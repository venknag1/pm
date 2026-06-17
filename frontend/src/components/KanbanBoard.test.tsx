import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, type Mock } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import * as api from "@/lib/api";
import { initialData } from "@/lib/kanban";

vi.mock("@/lib/api", () => ({
  getBoard: vi.fn(),
  renameColumn: vi.fn().mockResolvedValue(undefined),
  createCard: vi.fn().mockResolvedValue("test-card-id"),
  deleteCard: vi.fn().mockResolvedValue(undefined),
  moveCard: vi.fn().mockResolvedValue(undefined),
  sendAIMessage: vi.fn().mockResolvedValue({ reply: "I can help!", board: null }),
}));

const renderBoard = () => render(<KanbanBoard onLogout={() => {}} />);

beforeEach(() => {
  (api.getBoard as Mock).mockResolvedValue({
    columns: initialData.columns,
    cards: initialData.cards,
  });
});

describe("KanbanBoard", () => {

  it("renders five columns after loading", async () => {
    renderBoard();
    expect(await screen.findAllByTestId(/^column-/)).toHaveLength(5);
  });

  it("renames a column", async () => {
    renderBoard();
    const columns = await screen.findAllByTestId(/^column-/);
    const input = within(columns[0]).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    renderBoard();
    const columns = await screen.findAllByTestId(/^column-/);
    const column = columns[0];

    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    await userEvent.type(within(column).getByPlaceholderText(/card title/i), "New card");
    await userEvent.type(within(column).getByPlaceholderText(/details/i), "Notes");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(await screen.findByText("New card")).toBeInTheDocument();

    await userEvent.click(
      await within(column).findByRole("button", { name: /delete new card/i })
    );

    await waitFor(() => {
      expect(within(column).queryByText("New card")).not.toBeInTheDocument();
    });
  });
});

describe("AI sidebar", () => {
  it("shows an AI Chat button in the header", async () => {
    renderBoard();
    await screen.findAllByTestId(/^column-/);
    expect(screen.getByRole("button", { name: /ai chat/i })).toBeInTheDocument();
  });

  it("opens the sidebar when AI Chat is clicked", async () => {
    renderBoard();
    await screen.findAllByTestId(/^column-/);
    await userEvent.click(screen.getByRole("button", { name: /ai chat/i }));
    expect(screen.getByTestId("ai-sidebar")).toBeInTheDocument();
  });

  it("closes the sidebar via the close button", async () => {
    renderBoard();
    await screen.findAllByTestId(/^column-/);
    await userEvent.click(screen.getByRole("button", { name: /ai chat/i }));
    await userEvent.click(screen.getByRole("button", { name: /close ai sidebar/i }));
    expect(screen.queryByTestId("ai-sidebar")).not.toBeInTheDocument();
  });

  it("closes the sidebar via the backdrop", async () => {
    renderBoard();
    await screen.findAllByTestId(/^column-/);
    await userEvent.click(screen.getByRole("button", { name: /ai chat/i }));
    await userEvent.click(screen.getByTestId("ai-sidebar-backdrop"));
    expect(screen.queryByTestId("ai-sidebar")).not.toBeInTheDocument();
  });

  it("sends a message and shows user message and AI reply", async () => {
    (api.sendAIMessage as Mock).mockResolvedValue({ reply: "Board looks great!", board: null });
    renderBoard();
    await screen.findAllByTestId(/^column-/);
    await userEvent.click(screen.getByRole("button", { name: /ai chat/i }));

    await userEvent.type(screen.getByLabelText("AI message input"), "How is the board?");
    await userEvent.click(screen.getByRole("button", { name: /^send$/i }));

    expect(await screen.findByText("How is the board?")).toBeInTheDocument();
    expect(await screen.findByText("Board looks great!")).toBeInTheDocument();
  });

  it("applies board update returned by AI", async () => {
    const updatedBoard = {
      columns: initialData.columns.map((col) =>
        col.id === "col-backlog" ? { ...col, title: "AI Queue" } : col
      ),
      cards: initialData.cards,
    };
    (api.sendAIMessage as Mock).mockResolvedValue({ reply: "Renamed!", board: updatedBoard });
    renderBoard();
    await screen.findAllByTestId(/^column-/);
    await userEvent.click(screen.getByRole("button", { name: /ai chat/i }));

    await userEvent.type(screen.getByLabelText("AI message input"), "Rename Backlog");
    await userEvent.click(screen.getByRole("button", { name: /^send$/i }));

    await screen.findByText("Renamed!");
    await waitFor(() => {
      const inputs = screen.getAllByLabelText("Column title") as HTMLInputElement[];
      expect(inputs.map((inp) => inp.value)).toContain("AI Queue");
    });
  });
});
