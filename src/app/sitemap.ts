import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const primaryDomain = "https://soilstice.vercel.app";
  const now = new Date();

  return [
    {
      url: `${primaryDomain}`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 1.0,
    },
    {
      url: `${primaryDomain}/evidence`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.9,
    },
    {
      url: `${primaryDomain}/dashboard`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.8,
    },
    {
      url: `${primaryDomain}/fields`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.8,
    },
  ];
}
