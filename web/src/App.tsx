import { AnimatePresence } from "framer-motion";
import { Route, Routes, useLocation } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { PageTransition } from "@/components/PageTransition";
import { AnalyticsPage } from "@/pages/AnalyticsPage";
import { JobDetailPage } from "@/pages/JobDetailPage";
import { JobFormPage } from "@/pages/JobFormPage";
import { JobsListPage } from "@/pages/JobsListPage";

export default function App() {
  const location = useLocation();

  return (
    <Layout>
      <AnimatePresence mode="wait" initial={false}>
        <Routes location={location} key={location.pathname}>
          <Route
            path="/"
            element={
              <PageTransition>
                <JobsListPage />
              </PageTransition>
            }
          />
          <Route
            path="/jobs/new"
            element={
              <PageTransition>
                <JobFormPage />
              </PageTransition>
            }
          />
          <Route
            path="/jobs/:id/edit"
            element={
              <PageTransition>
                <JobFormPage />
              </PageTransition>
            }
          />
          <Route
            path="/jobs/:id"
            element={
              <PageTransition>
                <JobDetailPage />
              </PageTransition>
            }
          />
          <Route
            path="/analytics"
            element={
              <PageTransition>
                <AnalyticsPage />
              </PageTransition>
            }
          />
        </Routes>
      </AnimatePresence>
    </Layout>
  );
}
