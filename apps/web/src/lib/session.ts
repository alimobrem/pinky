import { toast } from "sonner";

let redirectScheduled = false;

function performLoginRedirect() {
  window.location.href = "/login";
}

function resetRedirectFlag() {
  redirectScheduled = false;
}

export function redirectToLogin() {
  if (redirectScheduled) return;
  redirectScheduled = true;
  toast.error("Session expired. Redirecting to login...");
  globalThis.setTimeout(performLoginRedirect, 2000);
  globalThis.setTimeout(resetRedirectFlag, 5000);
}
