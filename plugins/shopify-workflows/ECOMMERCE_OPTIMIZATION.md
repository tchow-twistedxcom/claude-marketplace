# E-Commerce Product Listing & Conversion Optimization Guide

**Purpose**: Comprehensive guide for optimizing Shopify product listings, collections, and conversion rates for law enforcement and tactical gear e-commerce.

**Target**: Dutyman e-commerce strategy - police gear, duty equipment, tactical accessories

---

## Table of Contents

1. [Product Listing SEO Optimization](#product-listing-seo-optimization)
2. [Conversion Rate Optimization (CRO)](#conversion-rate-optimization-cro)
3. [Collection Strategy & Organization](#collection-strategy--organization)
4. [Image & Media Optimization](#image--media-optimization)
5. [Pricing Strategy](#pricing-strategy)
6. [Product Quality Audit Framework](#product-quality-audit-framework)
7. [Complete Optimization Workflows](#complete-optimization-workflows)

---

## Product Listing SEO Optimization

### Product Title Optimization

**Formula**: `[Primary Keyword] - [Key Feature] - [Brand/Model]`

**Best Practices**:
- **Length**: 60-70 characters (optimal for search results)
- **Keyword Placement**: Front-load most important keywords
- **Specificity**: Include model numbers, materials, key features
- **Avoid**: ALL CAPS, excessive punctuation, keyword stuffing

**Examples for Police Gear**:
```
❌ Bad: "AWESOME POLICE DUTY BELT - BEST QUALITY!!!"
✅ Good: "Police Duty Belt 2.25" Nylon - Safariland Model 94 - Black"

❌ Bad: "Tactical Flashlight"
✅ Good: "Streamlight ProTac HL5 Tactical Flashlight - 3500 Lumens LED"

❌ Bad: "Body Armor Vest for Police Officers"
✅ Good: "NIJ Level IIIA Body Armor Vest - Concealable Carrier - Large"
```

**GraphQL Query for Title Audit**:
```graphql
query AuditProductTitles {
  products(first: 250, query: "status:active") {
    edges {
      node {
        id
        title
        handle
        productType
        vendor
      }
    }
  }
}
```

**Title Scoring Criteria**:
- Length 60-70 chars: +10 points
- Includes model/SKU: +10 points
- Front-loaded keywords: +10 points
- No ALL CAPS: +10 points
- Specific features included: +10 points
- **Total: /50 points**

### Product Description Optimization

**Structure Template**:
```markdown
## [Product Name] - [Key Benefit]

**Key Features:**
- Feature 1 with specific measurement/detail
- Feature 2 with material/construction detail
- Feature 3 with compatibility/standard
- Feature 4 with certification/rating
- Feature 5 with warranty/guarantee

**Why Law Enforcement Professionals Choose [Product]:**
[Benefit-focused paragraph addressing pain points]

**Technical Specifications:**
- Dimensions: [exact measurements]
- Material: [specific material with rating]
- Weight: [exact weight]
- Certifications: [NIJ, ANSI, etc.]
- Warranty: [coverage details]

**What's Included:**
- Item 1
- Item 2
- Item 3

**Shipping & Returns:**
[Brief policy statement with link]
```

**Length Guidelines**:
- **Minimum**: 150 words
- **Optimal**: 250-400 words
- **Maximum**: 600 words (avoid overwhelming)

**SEO Keywords Placement**:
- **Primary keyword**: First 100 words
- **Secondary keywords**: Throughout body
- **Long-tail keywords**: In specifications
- **LSI keywords**: Natural variation

**Description Scoring Criteria**:
- Length 250-400 words: +10 points
- Includes features (5+ bullets): +10 points
- Benefits-focused section: +10 points
- Technical specs included: +10 points
- Call-to-action present: +10 points
- Mobile-formatted (short paragraphs): +10 points
- **Total: /60 points**

### Meta Description Optimization

**Best Practices**:
- **Length**: 150-160 characters
- **Include**: Primary keyword, key benefit, call-to-action
- **Avoid**: Duplicate descriptions, keyword stuffing

**Formula**: `[Action Verb] [Product] [Key Benefit]. [Specification/Feature]. [Trust Signal/CTA]`

**Examples**:
```
❌ Bad: "Buy police duty belt from our store. We have the best prices and fast shipping."

✅ Good: "Shop Safariland Model 94 Police Duty Belt. 2.25" nylon, NIJ certified. Trusted by law enforcement nationwide. Free shipping over $75."
```

### Product Handle (URL Slug) Optimization

**Best Practices**:
- **Format**: lowercase, hyphens only, no underscores
- **Keywords**: Include primary keyword
- **Specificity**: Model numbers when relevant
- **Avoid**: Generic handles, numbers only, auto-generated codes

**Examples**:
```
❌ Bad: /products/product-123456
❌ Bad: /products/belt_police_duty
✅ Good: /products/safariland-94-duty-belt-225-nylon-black
✅ Good: /products/streamlight-protac-hl5-tactical-flashlight
```

### Image Alt Text Optimization

**Formula**: `[Product Type] - [Brand] [Model] - [Key Feature] - [View/Angle]`

**Best Practices**:
- **Length**: Under 125 characters
- **Keywords**: Include primary keyword naturally
- **Descriptive**: Describe what's in the image
- **Specific**: Include angle, feature shown

**Examples**:
```
❌ Bad: "image1.jpg"
❌ Bad: "police belt"
✅ Good: "Safariland 94 Police Duty Belt - 2.25 inch nylon construction - Black - Front view"
✅ Good: "Body armor carrier NIJ Level IIIA - Concealable vest - Side profile showing adjustment straps"
```

---

## Conversion Rate Optimization (CRO)

### Product Page Conversion Checklist

**Essential Elements** (Must Have):
- [ ] High-quality hero image (minimum 2000x2000px)
- [ ] 5-7 product images showing multiple angles
- [ ] Clear pricing (no confusion about final cost)
- [ ] Prominent "Add to Cart" button (above the fold)
- [ ] Product availability status (In Stock / Low Stock / Pre-Order)
- [ ] Brief feature bullets (3-5 key features)
- [ ] Trust signals (reviews, certifications, guarantees)
- [ ] Mobile-optimized layout (70%+ of traffic)
- [ ] Fast page load (<3 seconds)
- [ ] Clear return/shipping policy link

**Advanced Elements** (Nice to Have):
- [ ] Product video or 360° view
- [ ] Size/fit guide with visual charts
- [ ] Customer reviews with photos
- [ ] Related products / "Customers also bought"
- [ ] Urgency indicators (limited stock, sale countdown)
- [ ] Live chat or support contact
- [ ] Detailed specifications table
- [ ] FAQ accordion section
- [ ] Social proof (# of reviews, rating score)
- [ ] Secure checkout badges

### Trust Signals for Law Enforcement Market

**Certifications & Compliance**:
- NIJ (National Institute of Justice) ratings
- ANSI standards compliance
- ISO certifications
- Government/military approvals
- Lab testing reports

**Social Proof**:
- Customer reviews with verification
- Testimonials from law enforcement officers
- Case studies from departments
- "Used by [X] departments nationwide"
- Photos/videos from actual officers

**Guarantees & Warranties**:
- Manufacturer warranty details
- Money-back guarantee
- Lifetime replacement programs
- Hassle-free returns (especially important for body armor)

**Authority Indicators**:
- Years in business
- Industry partnerships
- Awards and recognition
- Professional memberships (NTOA, etc.)
- Government contractor status

### Urgency & Scarcity Tactics

**Inventory-Based**:
```html
<!-- Low stock warning -->
<div class="low-stock-alert">
  ⚠️ Only 3 left in stock - Order soon
</div>

<!-- High demand indicator -->
<div class="demand-indicator">
  🔥 15 people are viewing this item right now
</div>

<!-- Recent purchases -->
<div class="social-proof">
  ✓ 12 purchased in the last 24 hours
</div>
```

**Time-Based**:
```html
<!-- Sale countdown -->
<div class="sale-countdown">
  ⏰ Sale ends in: 2h 34m 18s
</div>

<!-- Shipping deadline -->
<div class="shipping-cutoff">
  📦 Order within 4 hours for same-day shipping
</div>
```

**Conditional**:
```html
<!-- Free shipping threshold -->
<div class="cart-incentive">
  🚚 Add $23.50 more for FREE shipping!
</div>

<!-- Bulk discount -->
<div class="volume-discount">
  💰 Buy 3+ and save 15% per item
</div>
```

### Mobile Conversion Optimization

**Critical Mobile Elements**:
- **Sticky Add to Cart**: Button visible while scrolling
- **Click-to-Call**: Phone number as tappable button
- **Simplified Navigation**: Hamburger menu, fewer clicks
- **Touch-Friendly**: Buttons min 44x44px
- **Fast Images**: WebP format, lazy loading
- **Simplified Checkout**: Guest checkout, autofill

**Mobile-First Description Format**:
- Short paragraphs (2-3 sentences max)
- Bullet points over long text
- Accordion for detailed specs
- Sticky product title at top
- Large, clear pricing

---

## Collection Strategy & Organization

### Collection Taxonomy for Police Gear

**Primary Categories** (Top-Level Navigation):
```
1. Duty Gear
   - Duty Belts & Accessories
   - Belt Keepers & Hardware
   - Holsters & Retention

2. Body Armor & Protection
   - Concealable Armor
   - Tactical Armor Carriers
   - Armor Plates & Inserts

3. Tactical Equipment
   - Flashlights & Lighting
   - Batons & Impact Weapons
   - OC Spray & Chemical Agents

4. Uniforms & Apparel
   - Tactical Pants & Shorts
   - Duty Shirts & Polos
   - Outerwear & Jackets

5. Footwear
   - Tactical Boots
   - Uniform Shoes
   - Boot Accessories

6. Training & Qualifications
   - Range Equipment
   - Training Ammunition
   - Target Systems

7. Vehicle Equipment
   - Patrol Equipment
   - Emergency Lighting
   - Vehicle Organization
```

**Cross-Cutting Collections** (Marketing/Sales):
```
- New Arrivals (last 30 days)
- Best Sellers (top 20% by volume)
- Sale & Clearance (discounted items)
- Bundle & Save (product bundles)
- Officer Essentials (starter kits)
- Department Bulk Orders
- Made in USA
- NIJ Certified Products
```

**Seasonal Collections**:
```
- Summer Duty Gear (moisture-wicking, lightweight)
- Winter Equipment (cold-weather gear)
- Budget Season (Q4 for department purchases)
- Academy Graduation (May/June/December)
```

### Smart Collection Rules

**Example: Best Sellers Collection**
```graphql
mutation CreateBestSellersCollection {
  collectionCreate(input: {
    title: "Best Selling Police Gear"
    descriptionHtml: "<p>Most popular duty gear trusted by law enforcement nationwide</p>"
    ruleSet: {
      appliedDisjunctively: false
      rules: [
        {
          column: TAG
          relation: EQUALS
          condition: "bestseller"
        },
        {
          column: INVENTORY_TOTAL
          relation: GREATER_THAN
          condition: "5"
        }
      ]
    }
  }) {
    collection { id title }
    userErrors { message }
  }
}
```

**Example: NIJ Certified Products**
```graphql
mutation CreateNIJCertifiedCollection {
  collectionCreate(input: {
    title: "NIJ Certified Body Armor & Equipment"
    ruleSet: {
      rules: [
        {
          column: TAG
          relation: EQUALS
          condition: "nij-certified"
        }
      ]
    }
  }) {
    collection { id }
    userErrors { message }
  }
}
```

**Example: Low Stock Alert Collection** (Internal Use)
```graphql
mutation CreateLowStockCollection {
  collectionCreate(input: {
    title: "Low Stock Alert - Reorder Soon"
    published: false  # Internal only
    ruleSet: {
      rules: [
        {
          column: INVENTORY_TOTAL
          relation: LESS_THAN
          condition: "10"
        },
        {
          column: TAG
          relation: EQUALS
          condition: "active-inventory"
        }
      ]
    }
  }) {
    collection { id }
    userErrors { message }
  }
}
```

### Collection SEO Optimization

**Collection Title Format**: `[Category] for [Target Audience] | [Brand]`

**Examples**:
```
✅ "Police Duty Belts & Accessories for Law Enforcement | Dutyman"
✅ "NIJ Certified Body Armor for Police Officers | Dutyman"
✅ "Tactical Flashlights & Lighting Equipment | Dutyman"
```

**Collection Description Template**:
```markdown
# [Collection Name] - [Key Benefit]

[Opening paragraph addressing target audience pain point and collection purpose]

## Featured [Category]:
- [Subcategory 1 with brief description]
- [Subcategory 2 with brief description]
- [Subcategory 3 with brief description]

## Why Choose Dutyman for [Category]:
✓ [Trust signal 1 - e.g., "Trusted by 1,000+ departments"]
✓ [Trust signal 2 - e.g., "NIJ certified products"]
✓ [Trust signal 3 - e.g., "30-day return policy"]

[Brief paragraph about quality, service, expertise]

**Questions?** Contact our expert team at [phone] or [email]
```

---

## Image & Media Optimization

### Product Photography Standards

**Minimum Requirements**:
- **Resolution**: 2000x2000px minimum (allows zoom)
- **Format**: JPEG for photos, PNG for graphics with transparency
- **File Size**: Under 500KB per image (use compression)
- **Background**: Pure white (#FFFFFF) for main images
- **Lighting**: Even, bright, no harsh shadows
- **Focus**: Sharp, no blur

**Required Image Types** (Minimum 5):
1. **Hero Image**: Product alone, main angle, white background
2. **Angled View**: 45° angle showing depth
3. **Detail Shot**: Close-up of key feature/quality
4. **In-Use**: Product worn/used (model or mannequin)
5. **Size Reference**: Product with measurement or common object

**Additional Recommended Images**:
6. Back view or alternate angle
7. Packaging/included accessories
8. Lifestyle shot in realistic setting
9. Infographic with specifications
10. Comparison with similar products

### Police Gear Specific Photography

**Body Armor**:
- Front view on torso form
- Back view showing adjustment straps
- Side profile showing thickness
- Detail shot of ballistic material/stitching
- Concealability comparison (under uniform shirt)
- Size chart with measurements

**Duty Belts**:
- Full belt with all accessories attached
- Close-up of buckle mechanism
- Material/stitching detail
- Worn on mannequin with accessories
- Measurement chart overlay

**Tactical Flashlights**:
- Lit and unlit comparison
- Size comparison (with hand or common object)
- Beam pattern demonstration
- Detail of controls/switches
- Battery compartment view

### Alt Text Formula by Image Type

**Hero Image**:
```
"[Brand] [Model] [Product Type] - [Primary Material] - [Color] - Front view"
Example: "Safariland Model 94 Police Duty Belt - Nylon construction - Black - Front view"
```

**Detail Shot**:
```
"[Product] detail showing [specific feature] - [Material/Construction detail]"
Example: "Duty belt detail showing reinforced stitching and stainless steel hardware"
```

**In-Use Image**:
```
"[Product Type] [model] worn by [user type] - [Setting/Context]"
Example: "NIJ Level IIIA body armor vest worn by police officer - Patrol duty"
```

### Image Optimization Workflow

**Step 1: Preparation**
```bash
# Batch resize to 2000x2000
mogrify -resize 2000x2000 -quality 85 *.jpg

# Convert to WebP for web
for img in *.jpg; do
  cwebp -q 85 "$img" -o "${img%.jpg}.webp"
done
```

**Step 2: Upload to Shopify CDN**
```graphql
mutation UploadProductImages($input: [ProductImageInput!]!) {
  productUpdateImages(productId: $productId, images: $input) {
    product {
      images(first: 10) {
        edges {
          node {
            id
            url
            altText
          }
        }
      }
    }
    userErrors { message }
  }
}
```

**Step 3: Set Alt Text**
```graphql
mutation UpdateImageAltText($imageId: ID!, $altText: String!) {
  productImageUpdate(
    productId: $productId
    image: {
      id: $imageId
      altText: $altText
    }
  ) {
    image { id altText }
    userErrors { message }
  }
}
```

---

## Pricing Strategy

### Pricing Psychology for Law Enforcement Market

**Price Point Analysis**:
- **Budget**: Under $50 (high-volume accessories)
- **Mid-Range**: $50-200 (quality duty gear)
- **Premium**: $200-500 (body armor, advanced equipment)
- **Specialized**: $500+ (complete systems, bulk orders)

**Psychological Pricing Tactics**:
```
❌ Avoid: $100.00 (too round, perceived as marked up)
✅ Better: $99.95 (classic charm pricing)
✅ Best: $99.97 (unique ending, tested well)

For premium items:
❌ Avoid: $299.99 (looks cheap)
✅ Better: $295 (clean, premium feel)
```

### Compare-at-Price Strategy

**When to Use**:
- ✅ Actual MSRP is higher (legitimate comparison)
- ✅ Previous price was higher (sale/clearance)
- ✅ Competitor pricing is higher (price match)
- ❌ Artificially inflated "original" price (misleading)

**Implementation**:
```graphql
mutation SetCompareAtPrice($variantId: ID!, $price: String!, $compareAtPrice: String!) {
  productVariantUpdate(
    input: {
      id: $variantId
      price: $price
      compareAtPrice: $compareAtPrice
    }
  ) {
    productVariant {
      price
      compareAtPrice
    }
    userErrors { message }
  }
}
```

**Display Best Practices**:
```html
<div class="pricing">
  <span class="original-price strikethrough">$129.95</span>
  <span class="sale-price">$99.97</span>
  <span class="savings">Save $30 (23%)</span>
</div>
```

### Bundle Pricing Strategy

**Bundle Types**:
1. **Complete Kit**: "Full Duty Belt Setup - Save 20%"
2. **Accessory Bundle**: "Belt + Keepers + Holster"
3. **Replacement Bundle**: "3-Pack Duty Belt Keepers"
4. **Seasonal Bundle**: "Winter Patrol Gear Package"

**Pricing Formula**:
```
Individual Prices: $50 + $30 + $40 + $25 = $145
Bundle Discount: 15-25% off
Bundle Price: $109.97-$123.25

Show savings: "Save $35 when you buy the complete kit!"
```

### Volume Pricing

**Implementation for Department Orders**:
```html
<div class="volume-pricing">
  <h3>Department Bulk Pricing:</h3>
  <ul>
    <li>1-4 units: $99.97 each</li>
    <li>5-19 units: $94.97 each (Save 5%)</li>
    <li>20-49 units: $89.97 each (Save 10%)</li>
    <li>50+ units: Contact for quote</li>
  </ul>
  <a href="/pages/bulk-orders">Request Department Quote</a>
</div>
```

---

## Product Quality Audit Framework

### Comprehensive Audit Query

```graphql
query ComprehensiveProductAudit($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    descriptionHtml

    seo {
      title
      description
    }

    images(first: 10) {
      edges {
        node {
          id
          url
          altText
          width
          height
        }
      }
    }

    variants(first: 50) {
      edges {
        node {
          id
          title
          sku
          price
          compareAtPrice
          inventoryQuantity
          weight
          weightUnit
          image { id url }

          selectedOptions {
            name
            value
          }
        }
      }
    }

    tags
    productType
    vendor
    status

    totalInventory
    createdAt
    updatedAt
    publishedAt

    collections(first: 10) {
      edges {
        node {
          id
          title
        }
      }
    }
  }
}
```

### Scoring System

**SEO Score** (40 points):
- Title length 60-70 chars: 5 points
- Title includes primary keyword: 5 points
- Custom SEO title set: 5 points
- Custom SEO description 150-160 chars: 5 points
- Handle is SEO-friendly (no numbers/codes): 5 points
- Description 250-400 words: 10 points
- Product type set and specific: 5 points

**Image Quality Score** (30 points):
- Minimum 5 images: 10 points
- All images 2000x2000px or larger: 10 points
- All images have descriptive alt text: 10 points

**Variant Setup Score** (15 points):
- Proper option names (not "Option1"): 5 points
- All variants have SKUs: 5 points
- Variants have individual images: 5 points

**Completeness Score** (15 points):
- Product type filled: 3 points
- Vendor filled: 2 points
- Weight specified: 3 points
- 5-15 tags applied: 5 points
- In at least one collection: 2 points

**Total Score**: 100 points

**Rating Scale**:
- 90-100: Excellent (optimize ready)
- 75-89: Good (minor improvements)
- 60-74: Fair (needs attention)
- Below 60: Poor (requires work)

### Automated Audit Script Pattern

```javascript
async function auditProduct(productId) {
  // 1. Fetch product data
  const product = await fetchProductData(productId);

  // 2. Calculate scores
  const seoScore = calculateSEOScore(product);
  const imageScore = calculateImageScore(product);
  const variantScore = calculateVariantScore(product);
  const completenessScore = calculateCompletenessScore(product);

  // 3. Generate recommendations
  const recommendations = [];

  if (product.title.length < 60 || product.title.length > 70) {
    recommendations.push({
      severity: 'medium',
      category: 'SEO',
      issue: 'Title length not optimal',
      current: `${product.title.length} characters`,
      recommendation: 'Adjust title to 60-70 characters',
      impact: 'Search visibility'
    });
  }

  if (!product.seo.title || !product.seo.description) {
    recommendations.push({
      severity: 'high',
      category: 'SEO',
      issue: 'Custom meta tags missing',
      recommendation: 'Add custom SEO title and description',
      impact: 'Search ranking and CTR'
    });
  }

  if (product.images.length < 5) {
    recommendations.push({
      severity: 'high',
      category: 'Images',
      issue: `Only ${product.images.length} images`,
      recommendation: 'Add minimum 5 images (hero, angles, detail, in-use, size)',
      impact: 'Conversion rate'
    });
  }

  // Check image alt text
  const missingAlt = product.images.filter(img => !img.altText || img.altText.length < 10);
  if (missingAlt.length > 0) {
    recommendations.push({
      severity: 'medium',
      category: 'SEO',
      issue: `${missingAlt.length} images missing alt text`,
      recommendation: 'Add descriptive alt text to all images',
      impact: 'SEO and accessibility'
    });
  }

  // Check variant setup
  const variantsWithoutImages = product.variants.filter(v => !v.image);
  if (variantsWithoutImages.length > 0 && product.variants.length > 1) {
    recommendations.push({
      severity: 'low',
      category: 'Variants',
      issue: `${variantsWithoutImages.length} variants without specific images`,
      recommendation: 'Assign images to each variant (especially for color options)',
      impact: 'User experience'
    });
  }

  // Return audit result
  return {
    productId: product.id,
    productTitle: product.title,
    scores: {
      seo: seoScore,
      images: imageScore,
      variants: variantScore,
      completeness: completenessScore,
      total: seoScore + imageScore + variantScore + completenessScore
    },
    rating: getRating(seoScore + imageScore + variantScore + completenessScore),
    recommendations: recommendations,
    priority: calculatePriorityScore(recommendations),
    auditedAt: new Date().toISOString()
  };
}

function getRating(score) {
  if (score >= 90) return 'Excellent';
  if (score >= 75) return 'Good';
  if (score >= 60) return 'Fair';
  return 'Poor';
}
```

---

## Complete Optimization Workflows

### Workflow 1: New Product Launch Optimization

**Phase 1: Product Setup**
1. Create product with optimal title (60-70 chars, keyword-rich)
2. Write benefit-focused description (250-400 words)
3. Set custom SEO title and meta description
4. Configure variants with proper option names
5. Assign unique SKUs to all variants

**Phase 2: Visual Assets**
1. Upload minimum 5 high-quality images (2000x2000px)
2. Add descriptive alt text to all images
3. Assign variant-specific images for color/style options
4. Add product video if available
5. Consider 360° view for complex products

**Phase 3: Taxonomy & Organization**
1. Set specific product type (e.g., "Duty Belts" not "Belts")
2. Add 5-15 relevant tags
3. Add to primary category collection
4. Add to relevant smart collections (New Arrivals, etc.)
5. Set vendor correctly

**Phase 4: Pricing & Inventory**
1. Research competitive pricing
2. Set psychological price point ($X.97 vs $X.00)
3. Add compare-at-price if applicable
4. Activate inventory at all locations
5. Set initial stock levels

**Phase 5: Conversion Optimization**
1. Add trust signals (certifications, reviews, guarantees)
2. Create urgency if appropriate (limited stock, sale)
3. Configure related products
4. Set up cross-sell recommendations
5. Test mobile layout

**Phase 6: Audit & Launch**
1. Run comprehensive product audit
2. Fix any issues flagged (score target: 85+)
3. Preview on mobile and desktop
4. Publish product
5. Monitor first 48 hours performance

### Workflow 2: Existing Product Optimization

**Step 1: Audit Current State**
```javascript
// Run audit on all active products
const products = await getAllActiveProducts();
const audits = [];

for (const product of products) {
  const audit = await auditProduct(product.id);
  audits.push(audit);
}

// Sort by priority (lowest scores first)
audits.sort((a, b) => a.scores.total - b.scores.total);

// Export top 50 products needing attention
const priorityProducts = audits.slice(0, 50);
exportToCsv(priorityProducts, 'products-to-optimize.csv');
```

**Step 2: Prioritize by Impact**
- **High Priority**: Best sellers with low scores (quick wins)
- **Medium Priority**: High-traffic products with fair scores
- **Low Priority**: Low-traffic products with poor scores

**Step 3: Systematic Improvement**
```javascript
// For each priority product
for (const product of priorityProducts) {
  // Fix SEO issues
  if (product.scores.seo < 35) {
    await updateProductSEO(product.id, {
      title: optimizeTitle(product.title),
      seoTitle: generateMetaTitle(product),
      seoDescription: generateMetaDescription(product),
      handle: optimizeHandle(product.handle)
    });
  }

  // Fix image issues
  if (product.scores.images < 25) {
    // Flag for photography team
    await flagForPhotography(product.id, product.recommendations);
  }

  // Fix variant issues
  if (product.scores.variants < 12) {
    await fixVariantSetup(product.id);
  }

  // Fix completeness issues
  if (product.scores.completeness < 12) {
    await improveProductData(product.id);
  }

  // Re-audit
  const newAudit = await auditProduct(product.id);
  console.log(`${product.productTitle}: ${product.scores.total} → ${newAudit.scores.total}`);
}
```

**Step 4: Monitor Performance**
- Track conversion rate before/after
- Monitor search rankings
- Review customer feedback
- Analyze time-on-page metrics
- Compare cart add rate

### Workflow 3: Collection Reorganization

**Step 1: Analyze Current Structure**
```graphql
query AnalyzeCollections {
  collections(first: 250) {
    edges {
      node {
        id
        title
        handle
        productsCount

        ruleSet {
          appliedDisjunctively
          rules {
            column
            relation
            condition
          }
        }
      }
    }
  }
}
```

**Step 2: Plan New Taxonomy**
- Define 5-7 primary categories
- Create cross-cutting collections
- Plan seasonal collections
- Design smart collection rules

**Step 3: Implement Smart Collections**
```javascript
const smartCollections = [
  {
    title: "Best Selling Police Gear",
    tag: "bestseller",
    minInventory: 5
  },
  {
    title: "New Arrivals - Last 30 Days",
    createdAfter: thirtyDaysAgo,
    status: "active"
  },
  {
    title: "Low Stock Alert",
    maxInventory: 10,
    published: false  // Internal only
  },
  {
    title: "NIJ Certified Products",
    tag: "nij-certified"
  }
];

for (const collection of smartCollections) {
  await createSmartCollection(collection);
}
```

**Step 4: Optimize Collection Pages**
- Add keyword-rich titles and descriptions
- Upload collection hero images
- Set proper sort order (bestselling, price, etc.)
- Add featured products
- Optimize for mobile browsing

**Step 5: Update Navigation**
- Create logical menu structure
- Limit top-level to 7 categories
- Use mega menu for deep categories
- Add "Shop by" alternative paths

---

## Quick Reference Checklists

### Pre-Launch Product Checklist

**SEO** (5 minutes):
- [ ] Title 60-70 characters with primary keyword
- [ ] Custom SEO title (different from product title)
- [ ] Meta description 150-160 characters
- [ ] SEO-friendly handle (lowercase-with-hyphens)
- [ ] Description 250-400 words with features + benefits

**Images** (10-20 minutes):
- [ ] Minimum 5 images uploaded
- [ ] All images 2000x2000px or larger
- [ ] Hero image on white background
- [ ] Descriptive alt text on all images (under 125 chars)
- [ ] Variant-specific images assigned

**Product Data** (5 minutes):
- [ ] Specific product type set
- [ ] Vendor filled in
- [ ] 5-15 relevant tags
- [ ] Weight specified (for shipping calculation)
- [ ] Added to appropriate collections

**Variants** (5 minutes):
- [ ] Proper option names (Size, Color, not Option1)
- [ ] Unique SKUs for all variants
- [ ] Prices set with psychological pricing (.97)
- [ ] Compare-at-price if applicable
- [ ] Inventory activated at all locations

**Conversion Elements** (5 minutes):
- [ ] Trust signals mentioned (certifications, warranty)
- [ ] Call-to-action clear
- [ ] Related products configured
- [ ] Mobile preview checked
- [ ] Product tested on staging

### Daily Operations Checklist

**Inventory Management**:
- [ ] Check low-stock alerts
- [ ] Update inventory from warehouse
- [ ] Flag products needing reorder
- [ ] Update pre-order estimates

**Order Processing**:
- [ ] Process new orders
- [ ] Update tracking information
- [ ] Handle customer inquiries
- [ ] Review and respond to reviews

**Product Updates**:
- [ ] Update sale/promotional pricing
- [ ] Add new arrival tags
- [ ] Remove expired promotions
- [ ] Update seasonal collections

**Performance Monitoring**:
- [ ] Review top sellers
- [ ] Check products with high cart abandonment
- [ ] Monitor search terms with no results
- [ ] Track conversion rate changes

---

**Last Updated**: 2025-11-07
**Next Review**: Quarterly or when significant platform changes occur
**Maintained by**: Dutyman E-Commerce Team
