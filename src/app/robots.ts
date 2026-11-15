import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const primaryDomain = "https://soilstice.vercel.app";

  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/evidence", "/fields", "/dashboard"],
        disallow: ["/api/", "/settings"],
      },
      {
        userAgent: "Googlebot",
        allow: ["/", "/evidence", "/fields", "/dashboard"],
        disallow: ["/api/", "/settings"],
      },
    ],
    sitemap: `${primaryDomain}/sitemap.xml`,
    host: primaryDomain,
  };
}
