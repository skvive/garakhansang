import raw from "@/data/garak-recipes.json";

export type GarakRecipe = {
  id: string;
  title: string;
  category: "수산" | "축산" | "농산";
  main: string;
  time: number;
  servings: number;
  sku: string;
  intro: string;
  ingredients: string[];
  steps: string[];
  safety: string;
  editorial_status: string;
  photo_caption: string;
  tags: string[];
};

export const GARAK_RECIPES = raw as GarakRecipe[];
export const recipeImage = (id: string) => `/garak-recipes/${id}.webp`;
export function findGarakRecipe(id: string) {
  return GARAK_RECIPES.find((r) => r.id === id) ?? null;
}
export function recipesForProduct(slug: string, limit = 5) {
  return GARAK_RECIPES.filter((r) => r.sku === slug).slice(0, limit);
}
