import React from "react";

interface ToastProps {
  message: string;
  type?: "success" | "error" | "info";
  onClose: () => void;
}

const bgColors = {
  success: "bg-green-600",
  error: "bg-red-600",
  info: "bg-blue-600"
};

const Toast: React.FC<ToastProps> = ({ message, type = "info", onClose }) => (
  <div
    className={`fixed bottom-8 right-8 z-50 px-6 py-4 rounded-lg shadow-lg text-white font-semibold transition-all duration-300 ${bgColors[type]}`}
    role="alert"
    aria-live="assertive"
  >
    <div className="flex items-center space-x-4">
      <span>{message}</span>
      <button
        onClick={onClose}
        className="ml-4 text-white hover:text-gray-200 focus:outline-none"
        aria-label="Close notification"
      >
        ×
      </button>
    </div>
  </div>
);

export default Toast;
