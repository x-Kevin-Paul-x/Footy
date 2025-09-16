const React = require("react");
require("@testing-library/jest-dom");

// Polyfills for Node/Jest environment
// TextEncoder / TextDecoder are required by some browser polyfills (react-router, etc.)
const { TextEncoder, TextDecoder } = require("util");
global.TextEncoder = global.TextEncoder || TextEncoder;
global.TextDecoder = global.TextDecoder || TextDecoder;

// Mock react-router-dom for tests to avoid real router and possible multiple-React issues.
// Provides simple Link and Router components and common hooks used in tests.
jest.mock("react-router-dom", () => {
  const React = require("react");
  return {
    Link: ({ to, children, ...props }) => React.createElement("a", { href: to, ...props }, children),
    MemoryRouter: ({ children }) => children,
    BrowserRouter: ({ children }) => children,
    useNavigate: () => () => {},
    useLocation: () => ({ pathname: "/" }),
    useParams: () => ({}),
  };
});
