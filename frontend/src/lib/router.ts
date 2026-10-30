import { useState, useEffect, useCallback } from "react";

export type AppRoute =
  | { name: "home" }
  | { name: "how-it-works" }
  | { name: "login"; redirectAfter?: string; initialTab?: "login" | "signup" }
  | { name: "requisitions" }
  | { name: "requisitions-new"; step?: number }
  | { name: "job-dashboard"; jobId: string }
  | { name: "job-candidates"; jobId: string }
  | { name: "job-candidates-add"; jobId: string }
  | { name: "job-candidate-dossier"; jobId: string; candidateId: string }
  | { name: "job-candidate-email"; jobId: string; candidateId: string }
  | { name: "job-pipeline"; jobId: string }
  | { name: "job-audit"; jobId: string }
  | { name: "audit" }
  | { name: "settings" }
  | { name: "session-expired"; returnTo?: string }
  | { name: "not-found"; path: string };

export function parsePath(pathname: string, search = ""): AppRoute {
  const normalized = pathname.replace(/\/+$/, "") || "/";
  const params = new URLSearchParams(search);

  if (normalized === "/") {
    return { name: "home" };
  }

  if (normalized === "/how-it-works") {
    return { name: "how-it-works" };
  }

  if (normalized === "/login") {
    const redirectAfter = params.get("redirect") || undefined;
    const tabParam = params.get("tab");
    const initialTab = tabParam === "signup" ? "signup" : "login";
    return { name: "login", redirectAfter, initialTab };
  }

  if (normalized === "/requisitions") {
    return { name: "requisitions" };
  }

  if (normalized === "/requisitions/new") {
    const stepParam = parseInt(params.get("step") || "1", 10);
    return { name: "requisitions-new", step: isNaN(stepParam) ? 1 : stepParam };
  }

  if (normalized === "/audit") {
    return { name: "audit" };
  }

  if (normalized === "/settings") {
    return { name: "settings" };
  }

  if (normalized === "/session-expired") {
    return { name: "session-expired", returnTo: params.get("returnTo") || undefined };
  }

  // Job-scoped routes: /jobs/:jobId/...
  const jobMatch = normalized.match(/^\/jobs\/([^/]+)(.*)$/);
  if (jobMatch) {
    const jobId = decodeURIComponent(jobMatch[1]!);
    const rest = jobMatch[2] || "";

    if (rest === "" || rest === "/") {
      return { name: "job-dashboard", jobId };
    }

    if (rest === "/candidates") {
      return { name: "job-candidates", jobId };
    }

    if (rest === "/candidates/add") {
      return { name: "job-candidates-add", jobId };
    }

    const emailMatch = rest.match(/^\/candidates\/([^/]+)\/email$/);
    if (emailMatch) {
      const candidateId = decodeURIComponent(emailMatch[1]!);
      return { name: "job-candidate-email", jobId, candidateId };
    }

    const dossierMatch = rest.match(/^\/candidates\/([^/]+)$/);
    if (dossierMatch) {
      const candidateId = decodeURIComponent(dossierMatch[1]!);
      return { name: "job-candidate-dossier", jobId, candidateId };
    }

    if (rest === "/pipeline") {
      return { name: "job-pipeline", jobId };
    }

    if (rest === "/audit") {
      return { name: "job-audit", jobId };
    }

    return { name: "not-found", path: normalized };
  }

  return { name: "not-found", path: normalized };
}

export function buildPath(route: AppRoute): string {
  switch (route.name) {
    case "home":
      return "/";
    case "how-it-works":
      return "/how-it-works";
    case "login": {
      const query = new URLSearchParams();
      if (route.redirectAfter) query.set("redirect", route.redirectAfter);
      if (route.initialTab === "signup") query.set("tab", "signup");
      const qs = query.toString();
      return qs ? `/login?${qs}` : "/login";
    }
    case "requisitions":
      return "/requisitions";
    case "requisitions-new":
      return route.step && route.step > 1 ? `/requisitions/new?step=${route.step}` : "/requisitions/new";
    case "job-dashboard":
      return `/jobs/${encodeURIComponent(route.jobId)}`;
    case "job-candidates":
      return `/jobs/${encodeURIComponent(route.jobId)}/candidates`;
    case "job-candidates-add":
      return `/jobs/${encodeURIComponent(route.jobId)}/candidates/add`;
    case "job-candidate-dossier":
      return `/jobs/${encodeURIComponent(route.jobId)}/candidates/${encodeURIComponent(route.candidateId)}`;
    case "job-candidate-email":
      return `/jobs/${encodeURIComponent(route.jobId)}/candidates/${encodeURIComponent(route.candidateId)}/email`;
    case "job-pipeline":
      return `/jobs/${encodeURIComponent(route.jobId)}/pipeline`;
    case "job-audit":
      return `/jobs/${encodeURIComponent(route.jobId)}/audit`;
    case "audit":
      return "/audit";
    case "settings":
      return "/settings";
    case "session-expired":
      return route.returnTo ? `/session-expired?returnTo=${encodeURIComponent(route.returnTo)}` : "/session-expired";
    case "not-found":
      return route.path || "/404";
  }
}

export function isProtectedRoute(route: AppRoute): boolean {
  return !(
    route.name === "home" ||
    route.name === "how-it-works" ||
    route.name === "login" ||
    route.name === "not-found" ||
    route.name === "session-expired"
  );
}

export function hasSidebar(route: AppRoute, isAuthenticated: boolean): boolean {
  if (!isAuthenticated) return false;
  return !(
    route.name === "home" ||
    route.name === "how-it-works" ||
    route.name === "login" ||
    route.name === "session-expired"
  );
}

export function getJobIdFromRoute(route: AppRoute): string | null {
  if (
    route.name === "job-dashboard" ||
    route.name === "job-candidates" ||
    route.name === "job-candidates-add" ||
    route.name === "job-candidate-dossier" ||
    route.name === "job-candidate-email" ||
    route.name === "job-pipeline" ||
    route.name === "job-audit"
  ) {
    return route.jobId;
  }
  return null;
}

export function useRouter() {
  const [currentRoute, setCurrentRoute] = useState<AppRoute>(() => {
    if (typeof window === "undefined") return { name: "home" };
    return parsePath(window.location.pathname, window.location.search);
  });

  useEffect(() => {
    const handlePopState = () => {
      setCurrentRoute(parsePath(window.location.pathname, window.location.search));
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = useCallback((target: string | AppRoute, replace = false) => {
    const url = typeof target === "string" ? target : buildPath(target);
    const parsed = typeof target === "string" ? parsePath(target) : target;

    if (typeof window !== "undefined") {
      if (replace) {
        window.history.replaceState({}, "", url);
      } else {
        window.history.pushState({}, "", url);
      }
    }
    setCurrentRoute(parsed);
  }, []);

  return { currentRoute, navigate };
}
