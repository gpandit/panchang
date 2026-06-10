import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Temple Display | The Pandit",
  description: "Digital display boards for places of worship.",
};

// Display boards render full-screen without the app shell nav rail
export default function DisplayLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
