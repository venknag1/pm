import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, type Mock } from "vitest";
import { CardModal } from "@/components/CardModal";
import * as api from "@/lib/api";
import type { Card } from "@/lib/kanban";

vi.mock("@/lib/api", () => ({
  updateCard: vi.fn().mockResolvedValue(undefined),
  assignCard: vi.fn().mockResolvedValue(undefined),
  archiveCard: vi.fn().mockResolvedValue(undefined),
  duplicateCard: vi.fn().mockResolvedValue({ id: "card-new" }),
  getChecklist: vi.fn().mockResolvedValue([]),
  addChecklistItem: vi.fn().mockResolvedValue({ id: "chk-1", title: "New item", completed: false, position: 0 }),
  updateChecklistItem: vi.fn().mockResolvedValue({ id: "chk-1", title: "New item", completed: true, position: 0 }),
  deleteChecklistItem: vi.fn().mockResolvedValue(undefined),
  getComments: vi.fn().mockResolvedValue([]),
  addComment: vi.fn().mockResolvedValue({ id: "c1", username: "user", content: "test", created_at: new Date().toISOString() }),
  deleteComment: vi.fn().mockResolvedValue(undefined),
}));

const CARD: Card = {
  id: "card-1",
  title: "Test card",
  details: "Some details",
  priority: "medium",
  label: null,
  due_date: null,
};

const USERS = [
  { id: 1, username: "alice" },
  { id: 2, username: "bob" },
];

const renderModal = (overrides: Partial<Card> = {}) => {
  const onClose = vi.fn();
  const onUpdate = vi.fn();
  const onDuplicate = vi.fn();
  render(
    <CardModal
      card={{ ...CARD, ...overrides }}
      users={USERS}
      onClose={onClose}
      onUpdate={onUpdate}
      onDuplicate={onDuplicate}
    />
  );
  return { onClose, onUpdate, onDuplicate };
};

describe("CardModal", () => {
  it("renders with card title", () => {
    renderModal();
    expect(screen.getByDisplayValue("Test card")).toBeInTheDocument();
  });

  it("shows close button", () => {
    renderModal();
    expect(screen.getByLabelText(/close card/i)).toBeInTheDocument();
  });

  it("shows all priority options", () => {
    renderModal();
    expect(screen.getByRole("button", { name: /low/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /medium/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /high/i })).toBeInTheDocument();
  });

  it("shows user dropdown with users", () => {
    renderModal();
    expect(screen.getByLabelText(/assigned to/i)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "alice" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "bob" })).toBeInTheDocument();
  });

  it("shows unassigned option", () => {
    renderModal();
    expect(screen.getByRole("option", { name: /unassigned/i })).toBeInTheDocument();
  });

  it("shows duplicate button", () => {
    renderModal();
    expect(screen.getByRole("button", { name: /duplicate/i })).toBeInTheDocument();
  });

  it("calls duplicateCard and onDuplicate when duplicate clicked", async () => {
    const user = userEvent.setup();
    const { onDuplicate } = renderModal();
    await user.click(screen.getByRole("button", { name: /duplicate/i }));
    await waitFor(() => expect(api.duplicateCard as Mock).toHaveBeenCalledWith("card-1"));
    expect(onDuplicate).toHaveBeenCalledWith("card-new");
  });

  it("shows checklist section header", () => {
    renderModal();
    expect(screen.getByText(/checklist/i)).toBeInTheDocument();
  });

  it("shows add item button", () => {
    renderModal();
    expect(screen.getByRole("button", { name: /\+ add item/i })).toBeInTheDocument();
  });

  it("shows add item form when + Add item clicked", async () => {
    const user = userEvent.setup();
    renderModal();
    await user.click(screen.getByRole("button", { name: /\+ add item/i }));
    expect(screen.getByPlaceholderText(/item title/i)).toBeInTheDocument();
  });

  it("calls addChecklistItem when item form submitted", async () => {
    const user = userEvent.setup();
    renderModal();
    await user.click(screen.getByRole("button", { name: /\+ add item/i }));
    await user.type(screen.getByPlaceholderText(/item title/i), "My task");
    await user.click(screen.getByRole("button", { name: /^add$/i }));
    await waitFor(() =>
      expect(api.addChecklistItem as Mock).toHaveBeenCalledWith("card-1", "My task")
    );
  });

  it("loads checklist on mount", async () => {
    (api.getChecklist as Mock).mockResolvedValue([
      { id: "chk-1", title: "Do something", completed: false, position: 0 },
    ]);
    renderModal();
    await waitFor(() => expect(screen.getByText("Do something")).toBeInTheDocument());
  });

  it("saves card on Save click", async () => {
    const user = userEvent.setup();
    renderModal();
    const titleInput = screen.getByDisplayValue("Test card");
    await user.clear(titleInput);
    await user.type(titleInput, "Updated title");
    await user.click(screen.getByRole("button", { name: /^save$/i }));
    await waitFor(() =>
      expect(api.updateCard as Mock).toHaveBeenCalledWith(
        "card-1",
        expect.objectContaining({ title: "Updated title" })
      )
    );
  });
});
