# Frontend Agent Notes

## Purpose

This file documents the current `frontend/` app so the implementation plan can move forward with a clear understanding of the existing codebase.

## Project structure

- `package.json` defines a Next.js 16 app using React 19.
- `src/app/page.tsx` is the app entry point and renders the main Kanban page.
- `src/components/` contains the Kanban UI components and form behavior.
- `src/lib/kanban.ts` contains the board data model, initial demo state, and drag-and-drop helpers.
- `tests/` contains Playwright end-to-end tests.
- `src/lib/kanban.test.ts` contains a unit test for the board move logic.

## App entry point

- `src/app/page.tsx` renders the `KanbanBoard` component.
- There is no server-side or backend integration in the current app.

## Main components

- `src/components/KanbanBoard.tsx`
  - Client component (`"use client"`).
  - Renders the full board UI, header, and drag-and-drop container.
  - Uses React state to hold `board: BoardData` and `activeCardId`.
  - Handles drag start/end, column rename, card add, and card delete.
  - Uses `@dnd-kit/core` for drag-and-drop and `@dnd-kit/sortable` for sortable card interactions.

- `src/components/KanbanColumn.tsx`
  - Renders a single kanban column.
  - Uses `useDroppable` to accept dragged cards.
  - Renders cards with `SortableContext` and maps card IDs to `KanbanCard`.
  - Includes an inline editable column title and a card creation form.

- `src/components/KanbanCard.tsx`
  - Renders an individual card.
  - Uses `useSortable` to make the card draggable.
  - Supports card deletion via a remove button.

- `src/components/KanbanCardPreview.tsx`
  - Renders the drag overlay preview while a card is being dragged.

- `src/components/NewCardForm.tsx`
  - Renders an add-card button and a small form for new card title/details.
  - Supports open/cancel state and controlled input values.

## Data model and logic

- `src/lib/kanban.ts`
  - Defines `Card`, `Column`, and `BoardData` TypeScript types.
  - Contains `initialData` with 5 columns and 8 demo cards.
  - Implements `moveCard(columns, activeId, overId)` to reorder cards within and across columns.
  - Provides `createId(prefix)` for generating simple unique IDs.
  - The board data model is fully local and reset on page refresh.

## Styling and layout

- Styling is implemented with Tailwind CSS v4 utility classes inside JSX.
- The app uses a custom visual design with gradients, rounded cards, and a responsive grid.
- `src/app/globals.css` controls global CSS variables and base styles for the theme.

## Tests

- Unit tests:
  - `src/lib/kanban.test.ts` verifies the `moveCard` helper for reordering cards.
- End-to-end tests:
  - `tests/kanban.spec.ts` covers loading the board, adding a card, and dragging a card between columns.

## Current limitations

- No backend or API integration exists.
- No authentication/login flow.
- Board state is stored only in React component state and resets on refresh.
- There is only one hardcoded board and no persistence layer.
- The AI chat feature is not present in the frontend.

## Build and test commands

- `npm install`
- `npm run dev`
- `npm run build`
- `npm run start`
- `npm run test:unit`
- `npm run test:e2e`
- `npm run test:all`

## Notes

This frontend is a complete local Kanban demo but it is intentionally a self-contained, client-only app. The next step is to integrate it with the backend and add persistence, authentication, and AI functionality as defined in the plan.