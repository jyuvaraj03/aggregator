import type { Account } from "./api";

export const COLORS = [
  { name: "Ocean", hex: "#1f6f94" },
  { name: "Cobalt", hex: "#2856b8" },
  { name: "Indigo", hex: "#3f3d9e" },
  { name: "Violet", hex: "#6a3fa8" },
  { name: "Plum", hex: "#7d3b78" },
  { name: "Orchid", hex: "#b04fa6" },
  { name: "Rose", hex: "#c23f6e" },
  { name: "Crimson", hex: "#b3202f" },
  { name: "Brick", hex: "#a8442a" },
  { name: "Saffron", hex: "#d97a1c" },
  { name: "Turmeric", hex: "#c79a12" },
  { name: "Olive", hex: "#6f7a24" },
  { name: "Leaf", hex: "#3f8a3a" },
  { name: "Emerald", hex: "#1e8064" },
  { name: "Teal", hex: "#18837f" },
  { name: "Peacock", hex: "#0d6e8c" },
  { name: "Slate", hex: "#4d5b70" },
  { name: "Graphite", hex: "#34383f" },
  { name: "Cocoa", hex: "#6b4a3a" },
  { name: "Sand", hex: "#9c8463" },
];

export const nextColor = (accounts: Account[]) =>
  Array.from({ length: 20 }, (_, i) => i).find(
    (i) => !accounts.some((account) => account.color === i),
  ) ?? accounts.length % 20;
