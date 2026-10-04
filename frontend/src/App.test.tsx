import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import App from "./App";
import { number } from "./format";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const settings = {
  model: "qwen2.5:3b",
  threshold: 0.65,
  polling_interval: 8,
  pipeline: "two_stage",
  context_messages: 4,
  notifications: true,
  notification_previews: false,
};
function mockApi() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input);
    const body = path.includes("messages")
      ? { items: [], total: 0 }
      : path.includes("settings")
        ? settings
        : path.includes("models")
          ? { models: [] }
          : path.includes("status")
            ? {
                fixture: true,
                source: "mock",
                persistent: false,
                health: "Fixture",
              }
            : { messages_processed: 0, important: 0 };
    return new Response(JSON.stringify(body), { status: 200 });
  });
}
it("does not fabricate missing metrics", () => {
  expect(number(null, "%")).toBe("—");
  expect(number(0, "%")).toBe("0%");
});
it("shows fixture provenance and empty inbox", async () => {
  mockApi();
  render(<App />);
  expect(
    await screen.findByText(/Synthetic messages and simulated verdicts/),
  ).toBeInTheDocument();
  expect(screen.getByText("A quieter inbox starts here")).toBeInTheDocument();
});
it("persists changed preferences through the local API", async () => {
  const fetch = mockApi();
  render(<App />);
  await screen.findByText(/Synthetic messages/);
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  fireEvent.click(
    screen.getByRole("switch", { name: "Desktop notifications" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Save preferences" }));
  await waitFor(() =>
    expect(fetch).toHaveBeenCalledWith(
      "/api/settings",
      expect.objectContaining({
        method: "PUT",
        body: expect.stringContaining('"notifications":false'),
      }),
    ),
  );
  expect(await screen.findByText(/Settings saved/)).toBeInTheDocument();
});
it("shows a backend error instead of made-up data", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Offline"));
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Offline");
});
