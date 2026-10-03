import type React from "react";
import { createBrowserRouter, Navigate } from "react-router";
import Layout from "./components/Layout";
import { Loading } from "./components/ui";
import DatasetsPage from "./pages/DatasetsPage";
import JobsPage from "./pages/JobsPage";
import NotFound from "./pages/NotFound";

// Pages that pull in the editor (CodeMirror) and charts (recharts) load lazily.
const lazyPage = (load: () => Promise<{ default: React.ComponentType }>) => async () => ({
  Component: (await load()).default,
});

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    hydrateFallbackElement: <Loading />,
    children: [
      { index: true, element: <Navigate to="/datasets" replace /> },
      { path: "datasets", element: <DatasetsPage /> },
      { path: "datasets/:id", lazy: lazyPage(() => import("./pages/DatasetPage")) },
      { path: "jobs", element: <JobsPage /> },
      { path: "jobs/:id", lazy: lazyPage(() => import("./pages/JobPage")) },
      { path: "rule-sets", lazy: lazyPage(() => import("./pages/RuleSetsPage")) },
      { path: "*", element: <NotFound /> },
    ],
  },
]);
