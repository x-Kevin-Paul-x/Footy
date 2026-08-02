import "@testing-library/jest-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import Toast from "./Toast";

describe("Toast", () => {
  it("renders the message and closes on button click", () => {
    const handleClose = jest.fn();
    render(<Toast message="Test notification" type="success" onClose={handleClose} />);
    expect(screen.getByText("Test notification")).toBeInTheDocument();
    const closeBtn = screen.getByLabelText(/close/i);
    expect(closeBtn).toBeInTheDocument();
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalled();
  });

  it("applies correct background color for error type", () => {
    render(<Toast message="Error!" type="error" onClose={() => { }} />);
    expect(screen.getByRole("alert")).toHaveClass("MuiAlert-colorError");
  });

  it("applies correct background color for success type", () => {
    render(<Toast message="Success!" type="success" onClose={() => { }} />);
    expect(screen.getByRole("alert")).toHaveClass("MuiAlert-colorSuccess");
  });

  it("applies correct background color for info type (default)", () => {
    render(<Toast message="Info!" onClose={() => { }} />);
    expect(screen.getByRole("alert")).toHaveClass("MuiAlert-colorInfo");
  });

  it("has proper accessibility attributes", () => {
    render(<Toast message="Accessible!" onClose={() => { }} />);
    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent("Accessible!");
  });
});
