import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    // Project overrides
    rules: {
      // Allow plain quotes/apostrophes in JSX content
      "react/no-unescaped-entities": "off",
      // Allow <a href="/"> in app router when intentional
      "@next/next/no-html-link-for-pages": "off",
    },
  },
];

export default eslintConfig;
