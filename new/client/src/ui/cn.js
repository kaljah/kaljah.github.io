import { clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// Teach tailwind-merge our font-size tokens so text-sm vs text-text are not confused.
const twMerge = extendTailwindMerge({
  extend: {
    theme: { text: ["xs", "sm", "base", "md", "lg", "xl", "2xl", "3xl"] },
  },
});

export const cn = (...inputs) => twMerge(clsx(inputs));
