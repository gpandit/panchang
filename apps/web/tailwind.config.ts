import type { Config } from "tailwindcss";
// TODO(design): theme values flow entirely from @pandit/design-tokens — the
// preset below is generated from packages/design-tokens/src/schema.ts and
// resolves to CSS custom properties. Do not add hardcoded colours/spacing here.
import { tokenPreset } from "@pandit/design-tokens/tailwind-preset";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: tokenPreset,
  plugins: [],
};

export default config;
