import { toast } from "sonner";

let redirectScheduled = false;

export function redirectToLogin() {
  if (redirectScheduled) return;
  redirectScheduled = true;
  toast.error("Session expired. Redirecting to login...");
  setTimeout(() => {
    window.location.href = "/login";
  }, 2000);
  setTimeout(() => {
    redirectScheduled = false;
  }, 5000);
}
