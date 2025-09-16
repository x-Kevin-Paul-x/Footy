import React from "react";
import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import Toast from "./Toast";

describe("Toast", () => {
  it("renders the message and closes on button click", () => {
    const handleClose = jest.fn();
    render(<Toast message="Test notification" type="success" onClose={handleClose} />);
    expect(screen.getByText("Test notification")).toBeInTheDocument();
    const closeBtn = screen.getByLabelText(/close notification/i);
    expect(closeBtn).toBeInTheDocument();
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalled();
  });

  it("applies correct background color for error type", () => {
    render(<Toast message="Error!" type="error" onClose={() => {}} />);
    expect(screen.getByRole("alert")).toHaveClass("bg-red-600");
  });

  it("applies correct background color for success type", () => {
    render(<Toast message="Success!" type="success" onClose={() => {}} />);
    expect(screen.getByRole("alert")).toHaveClass("bg-green-600");
  });

  it("applies correct background color for info type (default)", () => {
    render(<Toast message="Info!" onClose={() => {}} />);
    expect(screen.getByRole("alert")).toHaveClass("bg-blue-600");
  });

  it("has proper accessibility attributes", () => {
    render(<Toast message="Accessible!" onClose={() => {}} />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveAttribute("aria-live", "assertive");
    expect(alert).toHaveTextContent("Accessible!");
  });
});
