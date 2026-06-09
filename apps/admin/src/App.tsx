import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/contexts/AuthContext";
import { AuditPage } from "@/pages/AuditPage";
import { ContentPage } from "@/pages/ContentPage";
import { FestivalEditorPage } from "@/pages/FestivalEditorPage";
import { FlagsPage } from "@/pages/FlagsPage";
import { LoginPage } from "@/pages/LoginPage";
import { ReportsPage } from "@/pages/ReportsPage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/content" replace />} />
        <Route path="content" element={<ContentPage />} />
        <Route path="content/:id" element={<FestivalEditorPage />} />
        <Route path="flags" element={<FlagsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="audit" element={<AuditPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/content" replace />} />
    </Routes>
  );
}
