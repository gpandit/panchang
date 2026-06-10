import type { Metadata } from "next";
import { TempleDisplayClient } from "./TempleDisplayClient";

export const metadata: Metadata = {
  title: "Temple Display | The Pandit",
};

export default function DisplayPage() {
  return <TempleDisplayClient />;
}
