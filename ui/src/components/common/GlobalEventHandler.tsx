import { useEffect } from "react";
import { useToast } from "@/contexts/ToastContext";

export const GlobalEventHandler = () => {
  const toast = useToast();

  useEffect(() => {
    const handleShowToast = (event: Event) => {
      const customEvent = event as CustomEvent;
      if (customEvent.detail && customEvent.detail.message) {
        const { message, type, description } = customEvent.detail;
        if (type === "error") {
          toast.showError(message, { description });
        } else if (type === "success") {
          toast.showSuccess(message, { description });
        } else if (type === "info") {
          toast.showInfo(message, { description });
        } else if (type === "warning") {
          toast.showWarning(message, { description });
        }
      }
    };

    window.addEventListener("showToast", handleShowToast);

    return () => {
      window.removeEventListener("showToast", handleShowToast);
    };
  }, [toast]);

  return null;
};
