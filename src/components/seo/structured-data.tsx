export function StructuredData() {
  const primaryDomain = "https://soilstice.vercel.app";

  const websiteSchema = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": `${primaryDomain}/#website`,
    name: "SOILSTICE",
    alternateName: [
      "SOILSTICE Field Resilience Intelligence",
      "SOILSTICE Agriculture",
      "SOILSTICE NASA Space Apps"
    ],
    url: primaryDomain,
    description:
      "SOILSTICE transforms NASA Earth observations, USDA soil surveys and historical crop records into explainable field intelligence for smarter, climate-resilient agricultural decisions.",
    inLanguage: "en-US",
  };

  const organizationSchema = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "@id": `${primaryDomain}/#organization`,
    name: "SOILSTICE Research Team",
    url: primaryDomain,
    logo: {
      "@type": "ImageObject",
      url: `${primaryDomain}/icon-512.png`,
      width: "512",
      height: "512",
      caption: "SOILSTICE Logo",
    },
    sameAs: ["https://github.com/sc-likes-to-code/soilstice"],
    description:
      "Open-science agricultural intelligence research team participating in the NASA International Space Apps Challenge 2026.",
  };

  const webApplicationSchema = {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "@id": `${primaryDomain}/#webapp`,
    name: "SOILSTICE — Field Resilience Intelligence",
    url: primaryDomain,
    applicationCategory: "BusinessApplication, EducationalApplication",
    operatingSystem: "All modern web browsers (Chrome, Safari, Firefox, Edge) and mobile PWA",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
      availability: "https://schema.org/OnlineOnly",
    },
    browserRequirements: "Requires JavaScript. Requires HTML5 Canvas & WebGL support for interactive maps.",
    featureList: [
      "Field boundary delineation via USDA Crop Sequence Boundaries and custom parcels",
      "NASA POWER agrometeorological integration (precipitation, temperature extremes, GDD, reference ET0)",
      "USDA NRCS SSURGO high-resolution multi-depth soil profile queries (AWS 0-100cm, AWS 0-150cm, texture, pH, OM)",
      "USDA NASS Cropland Data Layer (CDL) 20-year sequence classification (2006-2025)",
      "NASA SRTM 30m digital elevation and slope curvature risk analysis",
      "Explainable crop suitability ranking based on Liebig's Law of the Minimum",
      "Four-pillar field resilience scoring across climate, soil, terrain, and rotation history",
      "Complete data provenance tracking and transparent scientific limitations register"
    ],
    provider: {
      "@type": "Organization",
      name: "SOILSTICE",
      url: primaryDomain,
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(webApplicationSchema) }}
      />
    </>
  );
}
