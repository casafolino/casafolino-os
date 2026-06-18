// basePath runtime per le fetch lato client: Next prefissa automaticamente
// <Link>/router, ma NON le fetch() esplicite. Inlinato a build time.
export const BP = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
